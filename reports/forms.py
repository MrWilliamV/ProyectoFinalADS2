# reports/forms.py
from django import forms
from inventory.models import Product, Location
from datetime import date


class Periodicity:
    """
    Defines the available periodicity options for the inventory report.
    """
    TRIMESTRAL = 'T'
    CUATRIMESTRAL = 'C'
    ANUAL = 'A'
    CHOICES = [
        (TRIMESTRAL, 'Trimestral'),
        (CUATRIMESTRAL, 'Cuatrimestral'),
        (ANUAL, 'Anual'),
    ]


def default_year() -> int:
    """
    Returns the current year to pre-fill the 'year' field.

    :return: Current year as integer.
    """
    return date.today().year


class InventoryReportForm(forms.Form):
    """
    Form for filtering and exporting inventory reports.

    It allows users to select a year, periodicity, location, product, and
    export format. Used in the 'inventory_report.html' template.

    Fields:
        year (IntegerField): Year of the report (defaults to current year).
        periodicity (ChoiceField): Time interval to group results (quarterly, four-month, or yearly).
        location (ModelChoiceField): Optional location filter (warehouse or store).
        product (ModelChoiceField): Optional product filter.
        export (ChoiceField): Export format (CSV or PDF).
    """

    year = forms.IntegerField(
        label="Año", min_value=2000, max_value=2100, initial=default_year,
        widget=forms.NumberInput(attrs={'class': 'input input-bordered w-32'})
    )

    periodicity = forms.ChoiceField(
        label="Periodicidad", choices=Periodicity.CHOICES, initial=Periodicity.TRIMESTRAL,
        widget=forms.Select(attrs={'class': 'select select-bordered'})
    )

    location = forms.ModelChoiceField(
        label="Ubicación", queryset=Location.objects.all(), required=False,
        widget=forms.Select(attrs={'class': 'select select-bordered'})
    )

    product = forms.ModelChoiceField(
        label="Producto", queryset=Product.objects.all(), required=False,
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'})
    )

    export = forms.ChoiceField(
        label="Exportar", required=False, choices=[('csv', 'CSV'), ('pdf', 'PDF')],
        widget=forms.Select(attrs={'class': 'select select-bordered'})
    )
