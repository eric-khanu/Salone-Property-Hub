"""Forms for submitting offline payments."""

from pathlib import Path

from django import forms
from django.utils import timezone

from .models import Payment


# Accepted payment-proof file extensions (checked alongside the file size).
PROOF_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
PROOF_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
DUPLICATE_WINDOW_MINUTES = 10


class PaymentSubmissionForm(forms.ModelForm):
    """Form for a user to submit an offline payment for verification.

    Required constructor arguments:
        plan  -- the Plan being paid for (sets the amount automatically)
        user  -- the User submitting the payment
    """

    class Meta:
        model = Payment
        fields = ["provider", "payer_name", "payment_date", "notes", "proof"]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": (
                        "Offline transaction ID / reference; "
                        "do not enter PINs or passwords."
                    ),
                }
            ),
        }

    def __init__(self, *args, plan=None, user=None, **kwargs):
        if plan is None or user is None:
            raise ValueError(
                "PaymentSubmissionForm requires both `plan=` and `user=`."
            )
        super().__init__(*args, **kwargs)
        self.plan = plan
        self.user = user

    # ---------------------------------------------------------------- validation
    def clean_proof(self):
        proof = self.cleaned_data.get("proof")
        if not proof:
            return proof

        if proof.size > PROOF_MAX_BYTES:
            raise forms.ValidationError(
                f"Payment proof must be {PROOF_MAX_BYTES // (1024 * 1024)} MB or smaller."
            )

        name = getattr(proof, "name", "") or ""
        ext = Path(name).suffix.lower()
        if ext not in PROOF_EXTENSIONS:
            raise forms.ValidationError(
                "Upload payment proof as JPG, PNG or PDF."
            )

        # Note: content-type is not verified. Renaming a .exe to .pdf will pass.
        # For stronger validation add python-magic or PyPDF2.
        return proof

    def clean_payment_date(self):
        payment_date = self.cleaned_data.get("payment_date")
        if payment_date and payment_date > timezone.localdate():
            raise forms.ValidationError("Payment date cannot be in the future.")
        return payment_date

    def clean(self):
        cleaned = super().clean()
        provider = cleaned.get("provider")

        # Soft duplicate guard: block identical pending submissions from the
        # same user for the same plan within a short window.
        if provider and self.user and self.plan:
            window_start = timezone.now() - timezone.timedelta(
                minutes=DUPLICATE_WINDOW_MINUTES
            )
            existing = Payment.objects.filter(
                user=self.user,
                plan=self.plan,
                provider=provider,
                status=Payment.Status.PENDING,
                created_at__gte=window_start,
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(
                    "You already submitted a pending payment for this plan "
                    "recently. Please wait for verification before submitting again."
                )
        return cleaned

    # ---------------------------------------------------------------- save
    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.user = self.user
        obj.plan = self.plan
        obj.amount_sle = self.plan.price_sle
        if commit:
            obj.save()
        return obj