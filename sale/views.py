from decimal import Decimal
from io import BytesIO  # (puede quedar si lo usas en otro lado)
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from HealthAndHouse.auth_rol import has_role
from product.models import Product

# === Importa SOLO lógica de negocio desde services.py ===
from .services import (
    get_store_location,
    find_product_by_code,
    available_stock_nonexpired,
    price_from_inventory,
    add_or_increment_cart_item,
    increment_cart_item,
    decrement_cart_item,
    remove_cart_item,
    current_qty_in_cart,
    make_sale_transaction,
)


@login_required
@has_role("ADMINISTRADOR", "VENDEDOR")
def sales(request):
    """
    Shows the POS page with the current cart and total.

    :param request: HttpRequest object.
    :return: Rendered 'sale.html' .
    :raises:
    """
    cart = request.session.get("cart", [])
    total = sum(Decimal(str(item.get("subtotal", 0))) for item in cart)
    return render(request, 'sale.html', {"cart": cart, "total": total})


@require_POST
@login_required()
def add_product_by_barcode(request):
    """
    Adds a product to the cart by reading POST fields used in your form.

    :param request: HttpRequest with POST
    :return: Redirect to sales with status message.
    :raises: ValueError  if validations fail.
    """
    code = (request.POST.get("id_product") or "").strip()
    if not code:
        messages.error(request, "Ingresa un código o código de barras.")
        return redirect('sales')

    try:
        qty_to_add = int(request.POST.get("quantity", "1"))
    except ValueError:
        qty_to_add = 1
    if qty_to_add <= 0:
        messages.warning(request, "La cantidad debe ser mayor que 0.")
        return redirect('sales')

    cart = request.session.get("cart", [])

    product = find_product_by_code(code)
    if not product:
        messages.error(request, f"No se encontró el producto para '{code}'.")
        return redirect('sales')

    store = get_store_location()
    if not store:
        messages.error(request, "No se encontró la ubicación de Tienda (ST).")
        return redirect('sales')

    disponible = available_stock_nonexpired(product, store)
    current_qty = current_qty_in_cart(cart, product)

    if Decimal(current_qty + qty_to_add) > disponible:
        messages.warning(request, f"Stock disponible en Tienda: {disponible}. No se puede agregar más.")
        return redirect('sales')

    price = price_from_inventory(product, store) or float(getattr(product, "price", 0) or 0.00)

    add_or_increment_cart_item(cart, product, qty_to_add, price)
    request.session["cart"] = cart
    request.session.modified = True

    return redirect('sales')


@require_POST
@login_required(login_url='login')
def add_qty(request, id_product):
    """
    Increases by one the quantity of a product already present in the cart.

    :param request: HttpRequest POST only).
    :param id_product: Product PK to increment in the cart.
    :return: Redirect to 'sales' with a status message.
    :raises: ValueError (messaged) if stock is insufficient.
    """
    cart = request.session.get("cart", [])
    product = get_object_or_404(Product, pk=id_product)

    store = get_store_location()
    if not store:
        messages.error(request, "No se encontró la ubicación de Tienda (ST).")
        return redirect('sales')

    disponible = available_stock_nonexpired(product, store)

    current_qty = current_qty_in_cart(cart, product)
    if Decimal(current_qty + 1) > disponible:
        messages.warning(request, f"Stock disponible en Tienda: {disponible}. No se puede agregar más.")
        return redirect('sales')

    increment_cart_item(cart, id_product=id_product)

    request.session["cart"] = cart
    request.session.modified = True
    return redirect('sales')


@require_POST
@login_required(login_url='login')
def dec_qty(request, id_product):
    """
    Decreases by one the quantity of a product; removes it if it reaches zero.

    :param request: HttpRequest (POST only).
    :param id_product: Product PK to decrement in the cart.
    :return: Redirect to 'sales' with info message.
    :raises:
    """
    cart = request.session.get("cart", [])
    decrement_cart_item(cart, id_product=id_product)

    request.session["cart"] = cart
    request.session.modified = True
    return redirect('sales')


@require_POST
@login_required(login_url='login')
def remove_product_from_cart(request, id_product):
    """
    Removes a product from the cart regardless of current quantity.

    :param request: HttpRequest (POST only).
    :param id_product: Product PK to remove from the cart.
    :return: Redirect to 'sales' with info message.
    :raises:
    """
    cart = request.session.get("cart", [])
    remove_cart_item(cart, id_product=id_product)

    request.session["cart"] = cart
    request.session.modified = True
    return redirect('sales')


@require_POST
@login_required
def make_a_sale(request):
    """
    Completes the sale, delegating all business logic to services:
    - Validates active inventory period and open cash session.
    - Verifies non-expired stock per item and consumes lots/inventory.
    - Registers cash movements.
    - Generates PDF bytes for the invoice.

    :param request: HttpRequest
    :return: HttpResponse PDF download .
    :raises: ValueError for validation/stock errors.
    """
    cart = request.session.get("cart", [])
    if not cart:
        messages.error(request, "No hay productos en el carrito.")
        return redirect("sales")

    store = get_store_location()
    if not store:
        messages.error(request, "No se encontró la ubicación de Tienda (ST).")
        return redirect("sales")

    # Copia para el PDF se hace dentro del service; aquí solo pasamos el carrito.
    raw_cash = (request.POST.get("cash_received") or "").strip()

    try:
        pdf_bytes, invoice_number, total, change = make_sale_transaction(
            cart=cart,
            store=store,
            cash_received_raw=raw_cash,
        )
    except ValueError as e:
        messages.error(request, f"No se pudo completar la venta: {e}")
        return redirect("sales")
    except Exception as e:
        messages.error(request, f"No se pudo completar la venta: {e}")
        return redirect("sales")

    # Limpiar carrito después de una venta exitosa
    request.session["cart"] = []
    request.session.modified = True

    # Devolver el PDF con el mismo nombre que ya usabas
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="factura_{invoice_number}.pdf"'
    response.write(pdf_bytes)
    return response
