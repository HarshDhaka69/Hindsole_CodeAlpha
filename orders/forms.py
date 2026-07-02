from django import forms

TEXT_INPUT_CLASSES = (
    "w-full rounded-soft border border-neutral-300 dark:border-neutral-600 "
    "bg-white dark:bg-neutral-800 px-4 py-2.5 text-fluid-sm text-neutral-900 dark:text-neutral-50"
)


class ShippingForm(forms.Form):
    shipping_full_name = forms.CharField(
        label="Full name", max_length=120, widget=forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES})
    )
    contact_email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": TEXT_INPUT_CLASSES, "inputmode": "email"}),
    )
    shipping_line1 = forms.CharField(
        label="Address line 1", max_length=200, widget=forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES})
    )
    shipping_line2 = forms.CharField(
        label="Address line 2", max_length=200, required=False, widget=forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES})
    )
    shipping_city = forms.CharField(
        label="City", max_length=100, widget=forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES})
    )
    shipping_state = forms.CharField(
        label="State", max_length=100, widget=forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES})
    )
    shipping_postal_code = forms.CharField(
        label="Postal code",
        max_length=20,
        widget=forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES, "inputmode": "numeric"}),
    )
    shipping_country = forms.CharField(
        label="Country", max_length=100, initial="India", widget=forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES})
    )
    shipping_phone_number = forms.CharField(
        label="Phone number",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": TEXT_INPUT_CLASSES, "type": "tel", "inputmode": "tel"}),
    )
    save_address = forms.BooleanField(
        label="Save this address to my account", required=False,
        widget=forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded text-accent-500"}),
    )
