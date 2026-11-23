from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from .models import Address

NEW_ADDRESS_FIELDS = ("recipient_name", "phone", "address_line", "city", "province", "postal_code")
phone_validator = RegexValidator(r"^\+?[0-9 \-]{7,20}$", "Enter a valid contact number, e.g. 0917 123 4567.")
postal_validator = RegexValidator(r"^[0-9A-Za-z\- ]{3,10}$", "Enter a valid postal code.")


class CheckoutForm(forms.Form):
    quantity = forms.IntegerField(label="Quantity", min_value=1, initial=1)
    address = forms.ModelChoiceField(queryset=Address.objects.none(), required=False, label="Saved address", empty_label="Use a new address below")
    recipient_name = forms.CharField(label="Recipient name", max_length=100, required=False)
    phone = forms.CharField(label="Contact number", max_length=20, required=False, validators=[phone_validator])
    address_line = forms.CharField(label="Street, building or unit", max_length=255, required=False)
    city = forms.CharField(label="City or municipality", max_length=100, required=False)
    province = forms.CharField(label="Province or region", max_length=100, required=False)
    postal_code = forms.CharField(label="Postal code", max_length=10, required=False, validators=[postal_validator])

    def __init__(self, *args, user, listing, **kwargs):
        super().__init__(*args, **kwargs)
        self.user, self.listing = user, listing
        self.fields["address"].queryset = Address.objects.filter(user=user)  # only own addresses
        self.fields["quantity"].widget.attrs.update(min=1, max=listing.quantity)

    def clean_quantity(self):
        qty = self.cleaned_data["quantity"]
        if qty > self.listing.quantity:
            raise ValidationError(f"Only {self.listing.quantity} available.")  # BR-14
        return qty

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("address"):  # BR-05: delivery details are required
            for name in NEW_ADDRESS_FIELDS:
                if name not in self.errors and not (cleaned.get(name) or "").strip():
                    self.add_error(name, "Required when you don't choose a saved address.")
        return cleaned

    def get_address(self):
        """Saved address, or a new one created for this user."""
        chosen = self.cleaned_data.get("address")
        if chosen:
            return chosen
        data = {name: self.cleaned_data[name].strip() for name in NEW_ADDRESS_FIELDS}
        return Address.objects.create(user=self.user, **data)
