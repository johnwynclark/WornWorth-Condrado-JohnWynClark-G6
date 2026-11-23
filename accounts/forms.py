from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User

MAX_PHOTO_BYTES = 2 * 1024 * 1024


class RegistrationForm(forms.ModelForm):
    ROLE_CHOICES = [
        (User.Role.BUYER, "Buyer: I want to shop secondhand clothing"),
        (User.Role.SELLER, "Seller: I want to list and sell my clothes"),
    ]

    role = forms.ChoiceField(label="I want to join as", choices=ROLE_CHOICES, widget=forms.RadioSelect, initial=User.Role.BUYER)
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="At least 8 characters. Avoid common or all-number passwords.",
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("full_name", "email", "phone")
        labels = {"full_name": "Full name", "phone": "Contact number (optional)"}
        widgets = {"email": forms.EmailInput(attrs={"autocomplete": "email"})}

    def clean_full_name(self):
        name = " ".join(self.cleaned_data["full_name"].split())
        if len(name) < 2:
            raise ValidationError("Enter your full name.")
        return name

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists. Log in instead.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        elif p1:
            candidate = User(email=cleaned.get("email", ""), full_name=cleaned.get("full_name", ""))
            try:
                validate_password(p1, candidate)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}))
    password = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))

    error_messages = {
        "invalid_login": "Incorrect email or password. Check your details and try again.",
        "inactive": "This account is suspended or deactivated. Contact WornWorth support.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class ProfileForm(forms.ModelForm):
    profile_photo = forms.ImageField(label="Profile photo", required=False, widget=forms.FileInput(attrs={"accept": "image/*"}))
    remove_photo = forms.BooleanField(label="Remove current photo", required=False)

    class Meta:
        model = User
        fields = ("full_name", "email", "phone", "profile_photo")
        labels = {"full_name": "Full name", "phone": "Contact number"}

    def clean_full_name(self):
        name = " ".join(self.cleaned_data["full_name"].split())
        if len(name) < 2:
            raise ValidationError("Enter your full name.")
        return name

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Another account already uses this email.")
        return email

    def clean_profile_photo(self):
        photo = self.cleaned_data.get("profile_photo")
        if photo and hasattr(photo, "size") and photo.size > MAX_PHOTO_BYTES:
            raise ValidationError("Photo must be 2 MB or smaller.")
        return photo

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("remove_photo") and "profile_photo" not in self.files:
            if user.profile_photo:
                user.profile_photo.delete(save=False)
            user.profile_photo = None
        if commit:
            user.save()
        return user


# --- Django admin forms for the custom user ---
class AdminCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "full_name", "role")

    def clean_password2(self):
        if self.cleaned_data.get("password1") != self.cleaned_data.get("password2"):
            raise ValidationError("Passwords do not match.")
        return self.cleaned_data["password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = user.email.lower()
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class AdminChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"
