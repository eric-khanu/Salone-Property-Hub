"""Form for submitting an inquiry from a property detail page."""

from django import forms

from .models import Inquiry


# Sent in an invisible input; bots fill it, humans don't. See clean_honeypot().
HONEYPOT_FIELD = "website"


class InquiryForm(forms.ModelForm):
    """Public-facing inquiry form. Preserves only the fields a visitor controls."""

    # Honeypot — hidden by CSS in the template. Not part of the model.
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "hp-field",
                "tabindex": "-1",
                "autocomplete": "off",
                "aria-hidden": "true",
            }
        ),
    )

    class Meta:
        model = Inquiry
        fields = ["name", "email", "phone", "message"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "autocomplete": "name",
                    "placeholder": "Your name",
                    "maxlength": "120",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "autocomplete": "email",
                    "placeholder": "you@example.com",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "type": "tel",
                    "autocomplete": "tel",
                    "placeholder": "+232 76 123456",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "rows": 4,
                    "maxlength": "2000",
                    "placeholder": (
                        "Ask about viewing times, availability, or any details "
                        "the listing doesn't cover."
                    ),
                }
            ),
        }

    def clean_honeypot(self):
        """Reject the submission silently if the hidden field was filled in."""
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""

    def clean_message(self):
        message = (self.cleaned_data.get("message") or "").strip()
        if len(message) < 10:
            raise forms.ValidationError(
                "Please write at least a short sentence so the owner can respond."
            )
        if len(message) > 2000:
            raise forms.ValidationError(
                "Message must be 2000 characters or fewer."
            )
        return message

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter your full name.")
        return name

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        # The model-level PHONE_VALIDATOR handles format; add a length floor
        # so a single-digit submission can't go through.
        if len(phone.replace(" ", "").replace("-", "")) < 7:
            raise forms.ValidationError("Please enter a full phone number.")
        return phone