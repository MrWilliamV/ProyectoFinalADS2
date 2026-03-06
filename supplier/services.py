# supplier/services.py
from django.db.models import Q
from django.shortcuts import get_object_or_404

from supplier.models import Supplier
from supplier.forms import SupplierForm


def filter_suppliers(q: str = "", status: str = "", only_active=None):
    """

    :param q: search keyword (matches name, email, phone, city, country)
    :param status: "active" or "inactive"
    :param only_active: backward compatibility with checkbox (true/on/1)
    :return: Returns a filtered list of suppliers.
    """
    q = (q or "").strip()
    status = (status or "").lower()
    suppliers = Supplier.objects.all().order_by("name")

    if q:
        suppliers = suppliers.filter(
            Q(name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q) |
            Q(city__icontains=q) |
            Q(country__icontains=q)
        )

    # Compatibilidad con checkbox antiguo
    if not status and str(only_active).lower() in ("1", "on", "true"):
        status = "active"

    if status == "active":
        suppliers = suppliers.filter(active=True)
    elif status == "inactive":
        suppliers = suppliers.filter(active=False)

    return suppliers


def get_supplier_or_404(pk: int) -> Supplier:
    """

    :param pk: id of the supplier
    :return: Returns a single supplier or raises 404 if not found.
    """
    return get_object_or_404(Supplier, pk=pk)


def build_supplier_form(data=None, instance: Supplier | None = None) -> SupplierForm:
    """
    Creates a supplier form ready for use.
    :param data: The form data, usually request.POST.
    :param instance: If given, the form will edit that supplier.
    :return: The built form, not saved yet.
    """
    return SupplierForm(data, instance=instance)


def save_supplier_form(form: SupplierForm) -> bool:
    """
    Saves the supplier form if it's valid.
    :param form:  The form instance to validate and save.
    :return: bool: True if saved successfully, False if the form was invalid.
    """
    if form.is_valid():
        form.save()
        return True
    return False


def toggle_supplier_active(pk: int) -> Supplier:
    """
    Changes the 'active' state of a supplier.

    :param pk: The supplier ID to switch active.
    :return: The updated supplier object with its new state.
    """
    supplier = get_supplier_or_404(pk)
    supplier.active = not supplier.active
    supplier.save()
    return supplier