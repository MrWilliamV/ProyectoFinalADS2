from django import forms
from supplier.models import Supplier


class SupplierForm(forms.ModelForm):
    """
    It is directly linked to the Supplier model and defines how each field
    should be displayed in the interface.
    """

    class Meta:
        model = Supplier

        # Fields that will appear in the form
        fields = ["name", "email", "phone", "city", "country", "notes", "active", "age"]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Enter supplier name"
                }
            ),
            # Text box for the supplier's name. Required and unique.

            "email": forms.EmailInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "example@email.com"
                }
            ),
            # Email field with validation. Used to store supplier's contact email.

            "phone": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "+502 5555 5555"
                }
            ),
            #  Input for supplier phone number. Accepts digits, spaces, + and -.

            "city": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "City"
                }
            ),
            #  Text box for the city where the supplier is located.

            "country": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Country"
                }
            ),
            #  Text box for the supplier’s country. Default is Guatemala.

            "notes": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered w-full",
                    "rows": 3,
                    "placeholder": "Additional information or comments"
                }
            ),
            #  Multi-line text area for notes or remarks about the supplier.

            "age": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Age (optional)"
                }
            ),
            #  Numeric field for supplier or representative’s age (optional).

            "active": forms.CheckboxInput(
                attrs={
                    "class": "toggle toggle-primary"
                }
            ),
            # Toggle button to mark the supplier as active or inactive.
        }
