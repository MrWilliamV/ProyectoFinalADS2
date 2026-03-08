from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from inventory.models import InventoryMovement, Product, Location, InventoryConfig


def parse_report_date(value, default=None):
    if value:
        try:
            return timezone.datetime.fromisoformat(value).date()
        except Exception:
            d = parse_date(value)
            if d:
                return d
    return default


def get_kardex_filters():
    return {
        "locations": Location.objects.all().order_by("code"),
        "products": Product.objects.all().order_by("name"),
        "periods": InventoryConfig.objects.all().order_by("-is_active", "-fecha_corte", "-id"),
    }


def build_kardex_report_data(*, period_id="", start_str="", end_str="", location_id="", product_id="", page=1):
    if period_id:
        period = InventoryConfig.objects.filter(pk=period_id).first()
    else:
        period = InventoryConfig.objects.filter(is_active=True).first()

    today = timezone.localdate()
    default_start = today - timedelta(days=30)
    default_end = today

    start_date = parse_report_date(start_str, None)
    end_date = parse_report_date(end_str, None)

    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date

    qs = (
        InventoryMovement.objects
        .select_related("product", "location", "lot")
        .order_by("-fecha", "-id_movement")
    )

    if period:
        qs = qs.filter(period=period)

    if start_date:
        qs = qs.filter(fecha__date__gte=start_date)
    if end_date:
        qs = qs.filter(fecha__date__lte=end_date)

    if location_id:
        qs = qs.filter(location__id_location=location_id)
    if product_id:
        qs = qs.filter(product__id_product=product_id)

    totals = qs.aggregate(
        entrada_cantidad=Sum("entrada_cantidad"),
        entrada_valor=Sum("entrada_valor"),
        salida_cantidad=Sum("salida_cantidad"),
        salida_valor=Sum("salida_valor"),
    )

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page or 1)

    return {
        "page_obj": page_obj,
        "totals": totals,
        "count": paginator.count,
        "start": start_date or default_start,
        "end": end_date or default_end,
        "selected_location": location_id,
        "selected_product": product_id,
        "current_period_id": period.id if period else None,
    }