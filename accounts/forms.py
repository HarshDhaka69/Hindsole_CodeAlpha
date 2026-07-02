from django import forms
from django.contrib.auth.forms import UserCreationForm

from products.models import SHOE_SIZE_CHOICES

from .models import Address, User

TEXT_INPUT_CLASSES = (
    "w-full rounded-soft border border-neutral-300 dark:border-neutral-600 "
    "bg-white dark:bg-neutral-800 px-4 py-2.5 text-fluid-sm text-neutral-900 dark:text-neutral-50 "
    "placeholder:text-neutral-400"
)


class SignupForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": TEXT_INPUT_CLASSES, "autocomplete": "email", "inputmode": "email"})
    )
    first_name = forms.CharField(
        max_length=150, required=False, widget=forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES})
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": TEXT_INPUT_CLASSES})
        self.fields["password2"].widget.attrs.update({"class": TEXT_INPUT_CLASSES})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    default_shoe_size = forms.ChoiceField(
        choices=[("", "Not set")] + SHOE_SIZE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": TEXT_INPUT_CLASSES}),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone_number", "default_shoe_size")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES}),
            "last_name": forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES}),
            "phone_number": forms.TextInput(
                attrs={"class": TEXT_INPUT_CLASSES, "type": "tel", "inputmode": "tel"}
            ),
        }


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = (
            "full_name",
            "line1",
            "line2",
            "city",
            "state",
            "postal_code",
            "country",
            "phone_number",
            "is_default",
        )
        widgets = {
            "full_name": forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES}),
            "line1": forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES}),
            "line2": forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES}),
            "city": forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES}),
            "state": forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES}),
            "postal_code": forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES, "inputmode": "numeric"}),
            "country": forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES}),
            "phone_number": forms.TextInput(
                attrs={"class": TEXT_INPUT_CLASSES, "type": "tel", "inputmode": "tel"}
            ),
            "is_default": forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded text-accent-500"}),
        }
