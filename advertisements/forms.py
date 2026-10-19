from django import forms
from .models import Advertisement
class AdvertisementForm(forms.ModelForm):
    def clean_image(self):
        image=self.cleaned_data.get('image')
        if image and image.size > 8*1024*1024:
            raise forms.ValidationError('Ad creative must be 8 MB or smaller.')
        return image
    class Meta:
        model=Advertisement
        fields=['title','image','landing_url','placement']
        widgets={'landing_url':forms.URLInput(attrs={'placeholder':'https://example.com'})}
