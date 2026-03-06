from django.core.exceptions import ValidationError
from django.db import reset_queries

from .models import Brand, Category, MeasureUnit

# forms.py
from django import forms
from .models import Product


class ProductForm(forms.ModelForm):
    """
    id_product (IntegerField): Manual PK (e.g., barcode/SKU).
        description (CharField): Short description (≤ 50 chars).
        name (CharField): Internal/technical name (≤ 45 chars).
        brand (ModelChoiceField): Product brand (required).
        category (ModelChoiceField): Product category (required).
        measure_unit (ModelChoiceField): Base unit (required).
        active (BooleanField): Whether the product can be used/sold.
        min_st (IntegerField): Minimum stock threshold for ST (store).
        max_st (IntegerField): Maximum stock threshold for ST (store).
        min_wh (IntegerField): Minimum stock threshold for WH (warehouse).
        max_wh (IntegerField): Maximum stock threshold for WH (warehouse).
    """
    min_st = forms.IntegerField(
        label="Mínimo (ST)", min_value=0, max_value=9999999, initial=0, required=True,
        widget=forms.NumberInput(attrs={
            "class": "input input-bordered w-full",
            "step": "1", "min": "0"
        })
    )

    max_st = forms.IntegerField(
        label="Máximo (ST)", min_value=0, max_value=9999999, initial=0, required=True,
        widget=forms.NumberInput(attrs={
            "class": "input input-bordered w-full",
            "step": "1", "min": "0"
        })
    )

    min_wh = forms.IntegerField(
        label="Mínimo (WH)", min_value=0, max_value=9999999, required=False, initial=0,
        widget=forms.NumberInput(attrs={
            "class": "input input-bordered w-full",
            "step": "1", "min": "0"
        })
    )

    max_wh = forms.IntegerField(
        label="Máximo (WH)", min_value=0, max_value=9999999, required=False, initial=0,
        widget=forms.NumberInput(attrs={
            "class": "input input-bordered w-full",
            "step": "1", "min": "0"
        })
    )

    brand = forms.ModelChoiceField(
        queryset=Brand.objects.all(),
        empty_label="-- Seleccione marca --",
        widget=forms.Select(attrs={"class": "select select-bordered w-full"})
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="-- Seleccione categoría --",
        widget=forms.Select(attrs={"class": "select select-bordered w-full"})
    )
    measure_unit = forms.ModelChoiceField(
        queryset=MeasureUnit.objects.all(),
        empty_label="-- Seleccione unidad --",
        widget=forms.Select(attrs={"class": "select select-bordered w-full"})
    )

    id_product = forms.IntegerField(
        max_value=9999999,
        min_value=0,
        required=True,
        widget=forms.NumberInput(attrs={"class": "input input-bordered w-full"})
    )

    name = forms.CharField(
        label="Nombre del producto",
        max_length=45,
        widget=forms.TextInput(attrs={
            "class": "input input-bordered w-full",
            "maxlength": 45,
            "placeholder": "Nombre del producto (máx. 45 caracteres)"
        })
    )

    description = forms.CharField(
        label="Descripción",
        max_length=50,
        required=False,
        widget=forms.Textarea(attrs={
            "class": "textarea textarea-bordered w-full min-h-28 resize-y "
                     "bg-base-200 text-base-content border-base-300 rounded-xl",
            "rows": 4,
            "maxlength": 50,
            "placeholder": "Breve descripción del producto... (máx. 50 caracteres)",
        })
    )

    active = forms.BooleanField(
        label="Activo",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "toggle"})
    )

    class Meta:
        model = Product
        fields = [
            "id_product", "description", "name",
            "brand", "category", "measure_unit",
            "active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si el producto ya existe (modo edición)
        if self.instance and self.instance.pk:
            # No requerir ni permitir editar el id
            self.fields["id_product"].required = False
            self.fields["id_product"].disabled = True

class BrandForm(forms.ModelForm):
    """
      name (CharField): Required, unique (case-insensitive).
        description (CharField): Optional short text (≤ 45 chars).

    """
    class Meta:
        model = Brand
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "input input-bordered w-full",
                "maxlength": 45,
                "placeholder": "Nombre de la marca"
            }),
            "description": forms.TextInput(attrs={
                "class": "input input-bordered w-full",
                "maxlength": 45,
                "placeholder": "Descripción (opcional)"
            }),
        }

    #Limpiar campos y validacion
    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise ValidationError("El nombre es obligatorio.")
        if Brand.objects.filter(name__iexact=name).exists():
            raise ValidationError("Ya existe una marca con este nombre.")
        return name

    def clean_description(self):
        return (self.cleaned_data.get("description") or "").strip()



class CategoryForm(forms.ModelForm):
    """
       category_name (CharField): Required, unique (case-insensitive).
        category_description (CharField): Optional short text (≤ 45 chars).

    """
    class Meta:
        model = Category
        fields = ["category_name", "category_description"]
        widgets = {
            "category_name": forms.TextInput(attrs={
                "class": "input input-bordered w-full",
                "maxlength": 45,
                "placeholder": "Nombre de la categoría"
            }),
            "category_description": forms.TextInput(attrs={
                "class": "input input-bordered w-full",
                "maxlength": 45,
                "placeholder": "Descripción (opcional)"
            }),
        }

    def clean_category_name(self):
        name = (self.cleaned_data.get("category_name") or "").strip()
        if not name:
            raise ValidationError("El nombre de la categoría es obligatorio.")
        if Category.objects.filter(category_name__iexact=name).exists():
            raise ValidationError("Ya existe una categoría con este nombre.")
        return name

    def clean_category_description(self):
        return (self.cleaned_data.get("category_description") or "").strip()



class MeasureUnitForm(forms.ModelForm):
    """
       code (CharField): Required, unique (case-insensitive), up to 10 chars.
        name (CharField): Required, up to 30 chars.
        active (BooleanField): Whether the unit is available.

    """
    class Meta:
        model = MeasureUnit
        fields = ["code", "name", "active"]
        widgets = {
            "code": forms.TextInput(attrs={
                "class": "input input-bordered w-full uppercase",
                "maxlength": 10,
                "placeholder": "Ej: UND, KG, ML"
            }),
            "name": forms.TextInput(attrs={
                "class": "input input-bordered w-full",
                "maxlength": 30,
                "placeholder": "Nombre de la unidad"
            }),
            "active": forms.CheckboxInput(attrs={"class": "toggle toggle-primary"}),
        }

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip().upper()
        if not code:
            raise ValidationError("El código es obligatorio.")
        if MeasureUnit.objects.filter(code__iexact=code).exists():
            raise ValidationError("Ya existe una unidad con este código.")
        return code

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise ValidationError("El nombre es obligatorio.")
        return name
