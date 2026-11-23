from django import forms
from django.core.exceptions import ValidationError

from .models import Category, Listing

MAX_IMAGE_BYTES = 3 * 1024 * 1024


def validate_image_size(image):
    if image.size > MAX_IMAGE_BYTES:
        raise ValidationError("Each photo must be 3 MB or smaller.")


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ("category", "title", "description", "price", "size", "condition", "quantity")
        labels = {"price": "Price (₱)", "quantity": "Quantity available"}
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "quantity": forms.NumberInput(attrs={"min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.all()
        self.fields["category"].empty_label = "Choose a category"

    def clean_title(self):
        title = " ".join(self.cleaned_data["title"].split())
        if len(title) < 3:
            raise ValidationError("Enter a title of at least 3 characters.")
        return title

    def clean_description(self):
        text = self.cleaned_data["description"].strip()
        if len(text) < 10:
            raise ValidationError("Describe the item in at least 10 characters (fit, flaws, material).")
        return text

    def clean_size(self):
        size = self.cleaned_data["size"].strip()
        if not size:
            raise ValidationError("Enter a size, e.g. S, M, 32 or One size.")
        return size


class ListingCreateForm(ListingForm):
    image = forms.ImageField(label="Main photo", required=False, validators=[validate_image_size], widget=forms.FileInput(attrs={"accept": "image/*"}))


class ListingImageForm(forms.Form):
    image = forms.ImageField(label="Add a photo", validators=[validate_image_size], widget=forms.FileInput(attrs={"accept": "image/*"}))


class ListingFilterForm(forms.Form):
    SORT_CHOICES = [("newest", "Newest first"), ("price_low", "Price: low to high"), ("price_high", "Price: high to low")]

    q = forms.CharField(label="Search", required=False, max_length=100)
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False, empty_label="All categories")
    size = forms.CharField(required=False, max_length=30)
    condition = forms.ChoiceField(required=False, choices=[("", "Any condition")] + list(Listing.Condition.choices))
    min_price = forms.DecimalField(label="Min price", required=False, min_value=0, decimal_places=2)
    max_price = forms.DecimalField(label="Max price", required=False, min_value=0, decimal_places=2)
    sort = forms.ChoiceField(required=False, choices=SORT_CHOICES)

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("min_price"), cleaned.get("max_price")
        if low is not None and high is not None and low > high:
            self.add_error("max_price", "Max price must be higher than min price.")
        return cleaned
