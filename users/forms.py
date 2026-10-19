"""Forms for user registration and profile editing."""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegisterForm(UserCreationForm):
    """Registration form for new users.

    Overrides model defaults so that:
      * ``role`` is required (the app gates plans and actions by it).
      * ``email`` must be unique (Django's AbstractUser doesn't enforce it).
      * Advertisers must supply a ``company_name``.
    """

    # Override to make it required — the model allows blank, but the app
    # cannot do anything useful with a role-less user.
    role = forms.ChoiceField(
        choices=User.Role.choices,
        required=True,
        widget=forms.Select(),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "phone",
            "whatsapp_number",
            "company_name",
        )
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": forms.TextInput(
                attrs={
                    "type": "tel",
                    "placeholder": "+232 76 123456",
                    "autocomplete": "tel",
                }
            ),
            "whatsapp_number": forms.TextInput(
                attrs={"type": "tel", "placeholder": "+232 76 123456"}
            ),
            "company_name": forms.TextInput(
                attrs={"placeholder": "Only required for company advertisers"}
            ),
        }

    # ---------------------------------------------------------------- validation
    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with that email address already exists."
            )
        return email

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        company = (cleaned.get("company_name") or "").strip()

        if role == User.Role.ADVERTISER and not company:
            self.add_error(
                "company_name",
                "Advertisers must supply a company name.",
            )

        # Normalise the stored value (trim, keep user's casing).
        cleaned["company_name"] = company
        return cleaned