from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from HealthAndHouse.auth_rol import has_role
from inventory.models import InventoryConfig
from inventory.forms import InventoryMoveForm
from inventory.models import Inventory, Location
from inventory.queries import get_inventory_filter_data, build_inventory_list_page
from inventory.services import registrar_entrada_compra, registrar_salida_inventario
from product.models import Product

Q2 = Decimal("0.01")
Q4 = Decimal("0.0001")


def _q2(x: Decimal) -> Decimal:
    return Decimal(x).quantize(Q2, rounding=ROUND_HALF_UP)


def _q4(x: Decimal) -> Decimal:
    return Decimal(x).quantize(Q4, rounding=ROUND_HALF_UP)


def _get_inv(pid, lid):
    if not pid or not lid:
        return None
    return Inventory.objects.filter(product_id=pid, location_id=lid).first()

@login_required()
@has_role("ADMINISTRADOR", "JEFE_ALMACEN")
def inventory_movement_view(request):
    raw_product_id = request.GET.get("product") or request.POST.get("product") or ""
    raw_location_id = request.GET.get("location") or request.POST.get("location") or ""

    def _to_int_or_none(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    product_id = _to_int_or_none(raw_product_id)
    location_id = _to_int_or_none(raw_location_id)

    inv = _get_inv(product_id, location_id)
    qty_meta = {
        "max": (inv.max_stock if inv and inv.max_stock is not None else None),
        "current": (inv.quantity if inv and inv.quantity is not None else None),
    }

    products = Product.objects.order_by("name")
    locations = Location.objects.order_by("name")

    if request.method == "POST":
        form = InventoryMoveForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            product = cd["product"]
            location = cd["location"]
            quantity = _q2(cd["quantity"])
            unit_cost = _q4(cd.get("unit_price_in") or Decimal("0.0000"))
            movement_type = cd["movement_type"]

            try:
                if movement_type in ["PUR", "ADJIN"]:
                    result = registrar_entrada_compra(
                        user=request.user,
                        product=product,
                        location=location,
                        quantity=quantity,
                        unit_cost=unit_cost,
                        lot_code=cd["lot_code"],
                        expire_date=cd.get("expire_date"),
                        supplier=cd["supplier"],
                        description=cd["descripcion"],
                        movement_type=movement_type,
                    )
                    unit = result["movement"].unidad
                    saldo = _q2(result["inventory"].quantity)
                    messages.success(request, f"Entrada registrada. Saldo actual: {saldo} {unit}.")
                    return redirect("see_inventory")

                elif movement_type in ["SAL", "ADJOUT"]:
                    result = registrar_salida_inventario(
                        user=request.user,
                        product=product,
                        location=location,
                        quantity=quantity,
                        description=cd["descripcion"],
                        movement_type=movement_type,
                    )
                    messages.success(
                        request,
                        f"Salida registrada. Saldo actual: {result['inventory'].quantity} {result['unit']}."
                    )
                    return redirect("see_inventory")

            except ValueError as e:
                form.add_error(None, str(e))
            except Exception as e:
                form.add_error(None, f"Ocurrió un error de sistema: {e}")

        return render(request, "inventory.html", {
            "form": form,
            "qty_meta": qty_meta,
            "products": products,
            "locations": locations,
            "product_id": product_id,
            "location_id": location_id,
        })

    initial = {}
    if product_id is not None:
        initial["product"] = product_id
    if location_id is not None:
        initial["location"] = location_id

    form = InventoryMoveForm(initial=initial)

    return render(request, "inventory.html", {
        "form": form,
        "qty_meta": qty_meta,
        "products": products,
        "locations": locations,
        "product_id": str(product_id) if product_id else "",
        "location_id": str(location_id) if location_id else "",
    })


@login_required
@has_role("ADMINISTRADOR", "JEFE_ALMACEN")
def inventory_list_view(request):
    q = request.GET.get("q", "").strip()
    loc_id = request.GET.get("location")
    sin_ini = request.GET.get("sin_ini") in ("1", "true", "yes")

    period_id = request.GET.get("period")
    if period_id:
        cfg = InventoryConfig.objects.filter(pk=period_id).first()
    else:
        cfg = InventoryConfig.objects.filter(is_active=True).first()

    filter_data = get_inventory_filter_data()
    locations = filter_data["locations"]
    periods = filter_data["periods"]

    if not cfg:
        return render(request, "see_inventory.html", {
            "page_obj": [],
            "locations": locations,
            "current_location": loc_id,
            "search": q,
            "no_active_period": True,
            "sin_ini": sin_ini,
            "periods": periods,
            "current_period_id": None,
        })

    page_obj = build_inventory_list_page(
        cfg=cfg,
        q=q,
        loc_id=loc_id,
        page_number=request.GET.get("page"),
    )

    return render(request, "see_inventory.html", {
        "page_obj": page_obj,
        "locations": locations,
        "current_location": loc_id,
        "search": q,
        "no_active_period": False,
        "sin_ini": sin_ini,
        "periods": periods,
        "current_period_id": cfg.id,
    })