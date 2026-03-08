from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import (
    F, Sum, Value, Max, DecimalField, Subquery, OuterRef, Case, When, Q
)
from django.db.models.functions import Coalesce

from product.models import Product
from inventory.models import InventoryConfig, InventoryMovement, LotStock, Location, Inventory, ProductLot


def build_inventory_list_page(*, cfg, q="", loc_id=None, page_number=1):
    ZERO_QTY = Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=4))
    ZERO_COST = Value(Decimal("0.0000"), output_field=DecimalField(max_digits=16, decimal_places=4))

    agg = (
        InventoryMovement.objects
        .filter(period=cfg)
        .values("lot_id", "location_id")
        .annotate(
            qty=Coalesce(Sum("entrada_cantidad"), ZERO_QTY) - Coalesce(Sum("salida_cantidad"), ZERO_QTY),
            avg=Coalesce(Max("valor_unitario"), ZERO_COST),
            updated_at=Max("fecha"),
        )
    )

    qs = (
        LotStock.objects
        .select_related("lot", "lot__product", "location")
        .annotate(
            row_id=F("id_lot_stock") if hasattr(LotStock, "id_lot_stock") else F("lot__id_lot"),
            product_id=F("lot__product__id_product"),
            lot_code=F("lot__lot_code"),
            id_lot=F("lot__id_lot"),
            name=F("lot__product__name"),
            expire_date=F("lot__expire_date"),
            period_qty=Coalesce(
                Subquery(
                    agg.values("qty").filter(
                        lot_id=OuterRef("lot_id"),
                        location_id=OuterRef("location_id")
                    )[:1]
                ),
                ZERO_QTY
            ),
            ls_qty=F("quantity"),
            display_qty=Case(
                When(period_qty__isnull=True, then=F("ls_qty")),
                When(period_qty__gt=F("ls_qty"), then=F("ls_qty")),
                default=F("period_qty"),
                output_field=DecimalField(max_digits=14, decimal_places=4),
            ),
            period_price=Coalesce(
                Subquery(
                    agg.values("avg").filter(
                        lot_id=OuterRef("lot_id"),
                        location_id=OuterRef("location_id")
                    )[:1]
                ),
                ZERO_COST
            ),
            updated_at=Subquery(
                agg.values("updated_at").filter(
                    lot_id=OuterRef("lot_id"),
                    location_id=OuterRef("location_id")
                )[:1]
            ),
        )
        .filter(display_qty__gt=0)
    )

    if loc_id:
        qs = qs.filter(location__id_location=loc_id)

    if q:
        filters = (
            Q(lot__product__name__icontains=q) |
            Q(lot__lot_code__icontains=q)
        )

        if q.isdigit():
            num = int(q)
            filters |= Q(lot__id_lot=num) | Q(lot__product__id_product=num)

        qs = qs.filter(filters)

    qs = qs.order_by("location__id_location", "name", "expire_date", "id_lot")

    rows = []
    for obj in qs:
        obj.quantity = obj.display_qty
        obj.price = obj.period_price
        rows.append(obj)

    paginator = Paginator(rows, 25)
    return paginator.get_page(page_number)


def get_inventory_filter_data():
    locations = Location.objects.all().order_by("id_location")
    periods = InventoryConfig.objects.all().order_by("-fecha_corte", "-id")
    return {
        "locations": locations,
        "periods": periods,
    }

def _current_stock_qty(product, location):
    """Stock actual = sum(entradas - salidas) para product+location."""
    agg = InventoryMovement.objects.filter(
        product=product, location=location
    ).aggregate(qty=Coalesce(Sum(F("entrada_cantidad") - F("salida_cantidad")), Value(Decimal("0.00"))))
    return agg["qty"] or Decimal("0.00")


def _stock_limits_for(product, location):
    """
    Obtiene min/max exclusivamente desde Inventory (por producto y ubicación).
    Si no existe registro Inventory, no aplica límites (None, None).
    """
    inv = Inventory.objects.filter(product=product, location=location).only("min_stock", "max_stock").first()
    if not inv:
        return (None, None)

    # normaliza a Decimal si son numéricos
    def _to_dec(x):
        if x is None:
            return None
        return Decimal(str(x))

    try:
        min_s = _to_dec(getattr(inv, "min_stock", None))
    except Exception:
        min_s = None
    try:
        max_s = _to_dec(getattr(inv, "max_stock", None))
    except Exception:
        max_s = None
    return (min_s, max_s)


# Encabezados EXACTOS del import/export de inventario inicial
INITIAL_HEADERS = [
    "codigo_producto",
    "nombre_producto",
    "lote",
    "fecha_vencimiento",
    "cantidad_de_producto",
    "precio",
    "unidad",
]


def _lot_code(lot: ProductLot) -> str:
    for f in ("code", "lot_code", "number", "name"):
        if hasattr(lot, f):
            return str(getattr(lot, f) or "")
    return ""


def _lot_expire(lot: ProductLot):
    for f in ("expire_date", "expiration_date", "due_date", "fecha_vencimiento"):
        if hasattr(lot, f):
            return getattr(lot, f)
    return None

def _product_unit(prod: Product) -> str:
    for f in ("unit", "unidad", "uom", "unidad_medida"):
        if hasattr(prod, f):
            val = getattr(prod, f)
            if val:
                return str(val)
    return "und"

def _avg_cost(prod: Product, location) -> Decimal:
    inv = Inventory.objects.filter(product=prod, location=location).first()
    if inv and getattr(inv, "avg_unit_cost", None) is not None:
        return inv.avg_unit_cost
    return Decimal("0.0000")


def _has_field(model_cls, name: str) -> bool:
    return any(f.name == name for f in model_cls._meta.get_fields())

