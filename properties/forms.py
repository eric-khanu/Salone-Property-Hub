"""Forms for creating and editing property listings."""

import json

from django import forms

from .models import Property, PropertyImage


# Sierra Leone's 16 districts/regions. Kept as a module constant so filter
# forms and admin can reuse it without duplicating the list.
REGION_CHOICES = [
    (x, x)
    for x in [
        "Western Area",
        "Western Area Rural",
        "Bo",
        "Bombali",
        "Bonthe",
        "Falaba",
        "Kailahun",
        "Kambia",
        "Karene",
        "Kenema",
        "Koinadugu",
        "Kono",
        "Moyamba",
        "Port Loko",
        "Pujehun",
        "Tonkolili",
    ]
]


class PropertyForm(forms.ModelForm):
    amenities = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"placeholder": "Water supply, Solar electricity, Security"}
        ),
        help_text=(
            "Comma-separated list, e.g. <em>Water supply, Solar electricity</em>. "
            "A JSON list is also accepted."
        ),
    )
    region = forms.ChoiceField(choices=REGION_CHOICES)

    class Meta:
        model = Property
        fields = [
            "title",
            "description",
            "listing_type",
            "property_type",
            "price",
            "currency",
            "region",
            "district_or_city",
            "neighborhood",
            "bedrooms",
            "bathrooms",
            "area_sqft",
            "amenities",
            "contact_phone",
            "whatsapp_number",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "price": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill the textarea from the instance so editing an existing
        # property doesn't blank out its amenities.
        if self.instance and self.instance.pk:
            amenities = self.instance.clean_amenities()
            if amenities:
                self.fields["amenities"].initial = ", ".join(amenities)

    def clean_amenities(self):
        """Accept a JSON list, a comma-separated string, or an actual list."""
        value = self.cleaned_data.get("amenities")

        if isinstance(value, list):
            return value
        if not value:
            return []

        if value.strip().startswith("["):
            try:
                data = json.loads(value)
            except (ValueError, TypeError):
                raise forms.ValidationError(
                    "Enter amenities as comma-separated values or a JSON list."
                )
        else:
            data = [x.strip() for x in value.split(",") if x.strip()]

        if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
            raise forms.ValidationError("Amenities must be text values.")

        return data


# ---------------------------------------------------------------------------
# Multi-file upload
# ---------------------------------------------------------------------------
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """An ImageField that accepts zero, one, or many files from a single input.

    Usage:
        images = MultipleImageField(required=False)              # any count
        images = MultipleImageField(required=True, min_files=1)  # at least 1
    """

    widget = MultipleFileInput

    def __init__(self, *args, min_files=0, **kwargs):
        self.min_files = min_files
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean

        if isinstance(data, (list, tuple)):
            files = [single_clean(item, initial) for item in data if item]
        else:
            files = [single_clean(data, initial)] if data else []

        if self.min_files and len(files) < self.min_files:
            raise forms.ValidationError(
                f"Please upload at least {self.min_files} "
                f"image{'s' if self.min_files != 1 else ''}."
            )

        return files