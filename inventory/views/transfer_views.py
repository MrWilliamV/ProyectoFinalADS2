from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Value, DecimalField, Sum, F, Subquery, OuterRef
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render

from HealthAndHouse.auth_rol import has_role
from inventory.models import ProductLot, Inventory, LotStock, InventoryConfig, Location, InventoryMovement
from inventory.services import registrar_transferencia_lote
from product.models import Product


@login_required
@has_role("ADMINISTRADOR", "JEFE_ALMACEN")
def traslado_lote_view(request):
    if request.method == "POST":
        origin_id = request.POST.get("origin")
        target_id = request.POST.get("to_location")
        selected = request.POST.get("selected")
        qty_raw = request.POST.get("quantity")

        if not selected:
            messages.error(request, "Selecciona un lote en la tabla.")
            return redirect("inventory_transfer")

        try:
            lot_id_str, product_id_str = selected.split(":")
            lot_id = int(lot_id_str)
            product_id = int(product_id_str)
        except Exception:
            messages.error(request, "Selección inválida.")
            return redirect("inventory_transfer")

        try:
            result = registrar_transferencia_lote(
                user=request.user,
                origin_id=origin_id,
                target_id=target_id,
                lot_id=lot_id,
                product_id=product_id,
                quantity=qty_raw,
            )
            messages.success(
                request,
                f"Traslado realizado: {result['quantity']} {result['movement_out'].unidad} "
                f"de {result['origin'].name} → {result['target'].name}."
            )
            return redirect("inventory_transfer")

        except ProductLot.DoesNotExist:
            messages.error(request, "El lote seleccionado no existe.")
        except Inventory.DoesNotExist:
            messages.error(request, "No existe inventario en el origen o destino.")
        except LotStock.DoesNotExist:
            messages.error(request, "No hay stock de ese lote en el origen.")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Ocurrió un error: {e}")

        return redirect("inventory_transfer")

    cfg = InventoryConfig.objects.filter(is_active=True).first()

    selected_product = (request.GET.get("product") or "").strip()

    origin_id = request.GET.get("origin")
    if not origin_id:
        first_loc = Location.objects.order_by("id_location").first()
        origin_id = str(first_loc.pk) if first_loc else ""

    locations = Location.objects.all().order_by("id_location")
    products = Product.objects.all().order_by("name")

    if cfg and origin_id:
        ZERO_QTY = Value(0, output_field=DecimalField(max_digits=14, decimal_places=4))

        movs = InventoryMovement.objects.filter(period=cfg, location_id=origin_id)
        agg = (
            movs.values("lot_id", "location_id")
                .annotate(
                    entradas=Coalesce(Sum("entrada_cantidad"), ZERO_QTY),
                    salidas=Coalesce(Sum("salida_cantidad"), ZERO_QTY),
                )
                .annotate(period_qty=F("entradas") - F("salidas"))
        )

        rows = (
            LotStock.objects
            .select_related("lot", "lot__product", "location")
            .filter(location_id=origin_id)
            .annotate(
                product_id=F("lot__product_id"),
                product_name=F("lot__product__name"),
                lot_pk=F("lot_id"),
                lot_code=F("lot__lot_code"),
                expire_date=F("lot__expire_date"),
                period_qty=Coalesce(Subquery(
                    agg.filter(
                        lot_id=OuterRef("lot_id"),
                        location_id=OuterRef("location_id")
                    ).values("period_qty")[:1]
                ), ZERO_QTY),
            )
            .filter(period_qty__gt=0)
            .order_by("product_name", "expire_date", "lot_code")
        )

        if selected_product:
            rows = rows.filter(lot__product_id=selected_product)

        paginator = Paginator(rows, 20)
        page_obj = paginator.get_page(request.GET.get("page"))
    else:
        paginator = Paginator([], 20)
        page_obj = paginator.get_page(1)

    context = {
        "locations": locations,
        "products": products,
        "origin_id": origin_id,
        "selected_product": selected_product,
        "page_obj": page_obj,
        "no_active_period": (cfg is None),
    }
    return render(request, "inventory_transfer.html", context)