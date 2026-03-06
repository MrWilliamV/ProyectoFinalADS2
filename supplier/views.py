from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from HealthAndHouse.auth_rol import has_role
from supplier.forms import SupplierForm
from supplier.services import (
    filter_suppliers,
    get_supplier_or_404,
    build_supplier_form,
    save_supplier_form,
    toggle_supplier_active,
)


# Create your views here.
@login_required
@has_role("ADMINISTRADOR")
def list_suppliers(request):
    """
    Displays a list of suppliers with optional filters.
    :param request: HTTP request object.
    :return: Rendered template with a filtered list of suppliers.
    """
    q = request.GET.get("q")
    status = request.GET.get("status")
    only_active = request.GET.get("only_active")

    suppliers = filter_suppliers(q=q, status=status, only_active=only_active)

    return render(request, "supplier_list.html", {
        "suppliers": suppliers,
    })


@login_required
@has_role("ADMINISTRADOR")
def create_supplier(request):
    """
     Handles the creation of a new supplier.
    :param request: HTTP request object.
    :return:    Redirect to the supplier list after success, or re-renders the form with error messages.
    """
    if request.method == "POST":
        form = build_supplier_form(request.POST)
        if save_supplier_form(form):
            messages.success(request, "Proveedor creado correctamente")
            return redirect('list_suppliers')
        else:
            messages.error(request, "Parece que faltan campos o no están completos")
    else:
        form = SupplierForm()

    return render(request, 'supplier_form.html', {'form': form})


@login_required
@has_role("ADMINISTRADOR")
def supplier_detail(request, pk):
    """
    Shows detailed information about one supplier.
    :param request: HTTP request object.
    :param pk: Supplier ID to display.
    :return: Redirect to the supplier detail page.
    """
    supplier = get_supplier_or_404(pk)
    return render(request, "supplier_detail.html", {"supplier": supplier})


@login_required()
@has_role("ADMINISTRADOR")
def supplier_update(request, pk):
    """
    Updates an existing supplier.

    :param request: HTTP request object.
    :param pk: Supplier ID to update.
    :return: Redirect to list of suppliers or supplier form.
    """
    supplier = get_supplier_or_404(pk)

    if request.method == "POST":
        form = build_supplier_form(request.POST, instance=supplier)
        if save_supplier_form(form):
            messages.success(request, "Proveedor actualizado correctamente.")
            return redirect("list_suppliers")
        else:
            messages.error(request, "Revisa los campos resaltados.")
    else:
        form = build_supplier_form(instance=supplier)

    return render(request, "supplier_form.html", {"form": form, "suppliers": supplier})


@login_required()
@has_role("ADMINISTRADOR")
def is_active_supplier(request, pk):
    """
    Toggles the active/inactive status of a supplier.
    :param request:  HTTP request object.
    :param pk: Supplier ID to toggle.
    :return: Redirects back to the supplier list with a success message.
    """
    if request.method == "POST":
        supplier = toggle_supplier_active(pk)
        state = "activado" if supplier.active else "desactivado"
        messages.success(request, f"Proveedor '{supplier.name}' {state} correctamente.")
    return redirect("list_suppliers")
