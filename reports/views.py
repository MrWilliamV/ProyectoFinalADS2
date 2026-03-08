
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.backends.ddl_references import Table
from django.utils import timezone
from django.db.models import Sum
from django.utils.dateparse import parse_date

from CashRegister.models import CashSession
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from HealthAndHouse.auth_rol import has_role
from inventory.models import InventoryMovement, Product, Location, InventoryConfig
from decimal import Decimal
from datetime import date
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import csv
from io import StringIO

from reports.queries import build_kardex_report_data, get_kardex_filters


@login_required
@has_role("ADMINISTRADOR", "AUDITOR")
def kardex_report(request):
    report_data = build_kardex_report_data(
        period_id=(request.GET.get("period") or "").strip(),
        start_str=request.GET.get("start") or "",
        end_str=request.GET.get("end") or "",
        location_id=(request.GET.get("location") or "").strip(),
        product_id=(request.GET.get("product") or "").strip(),
        page=request.GET.get("page") or 1,
    )

    filters = get_kardex_filters()

    context = {
        "page_obj": report_data["page_obj"],
        "totals": report_data["totals"],
        "start": report_data["start"],
        "end": report_data["end"],
        "count": report_data["count"],
        "locations": filters["locations"],
        "products": filters["products"],
        "selected_location": report_data["selected_location"],
        "selected_product": report_data["selected_product"],
        "periods": filters["periods"],
        "current_period_id": report_data["current_period_id"],
    }
    return render(request, "kardex.html", context)

User = get_user_model()
MOVEMENT_CHOICES = (
    ("", "Todos"),
    ("SALE", "Ventas"),
    ("INCOME", "Ingresos"),
    ("EXPENSE", "Egresos"),
)


def _parse_date_safe(value, default=None):
    if value:
        d = parse_date(value)
        if d:
            return d
    return default

@login_required
@has_role("ADMINISTRADOR", "AUDITOR")
def cash_report(request):
    # Filtros
    start_date_str = request.GET.get("start_date", "")
    end_date_str   = request.GET.get("end_date", "")
    cashier_id     = request.GET.get("cashier", "")

    today = timezone.localdate()
    start_date = _parse_date_safe(start_date_str, default=today)
    end_date   = _parse_date_safe(end_date_str, default=today)

    # Base queryset
    qs = CashSession.objects.select_related("cashier")

    # Filtros por fecha y cajero
    if start_date:
        qs = qs.filter(opened_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(opened_at__date__lte=end_date)
    if cashier_id:
        qs = qs.filter(cashier_id=cashier_id)

    #AGREGADOS
    from django.db.models import Count, Sum, Q, Value, DecimalField, F
    from django.db.models.functions import Coalesce

    zero = Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2))

    sales_sum   = Coalesce(Sum("movements__amount", filter=Q(movements__mtype__iexact="DEPOSITO")), zero)
    sales_count = Count("movements", filter=Q(movements__mtype__iexact="DEPOSITO"))
    expense_sum = Coalesce(Sum("movements__amount", filter=Q(movements__mtype__iexact="RETIRO")), zero)

    qs = qs.annotate(
        total_sales=sales_sum,
        sales_count=sales_count,
        total_expense=expense_sum,
        total_difference=F("total_sales") - F("total_expense"),
    ).order_by("-opened_at").distinct()

    # Metricas globales
    session_count        = qs.count()
    agg_total_sales      = sum((s.total_sales or Decimal("0.00")) for s in qs)
    agg_total_expense    = sum((s.total_expense or Decimal("0.00")) for s in qs)
    agg_sales_count      = sum((getattr(s, "sales_count", 0) or 0) for s in qs)
    agg_total_difference = agg_total_sales - agg_total_expense

    # Exportar CSV
    if request.GET.get("export") == "csv":
        buffer = StringIO()
        writer = csv.writer(buffer, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        # Encabezados
        writer.writerow([
            "Apertura",
            "Cierre",
            "Cajero",
            "Cant. Ventas",
            "Apertura (Inicial)",
            "Total Ventas",
            "Total Egresos",
            "Diferencia",
        ])

        # Filas
        for s in qs:
            cashier_name = ""
            if s.cashier:
                fn = getattr(s.cashier, "get_full_name", lambda: "")()
                cashier_name = fn or getattr(s.cashier, "username", "")

            writer.writerow([
                s.opened_at.strftime("%Y-%m-%d %H:%M:%S") if s.opened_at else "",
                s.closed_at.strftime("%Y-%m-%d %H:%M:%S") if s.closed_at else "",
                cashier_name,
                s.sales_count or 0,
                f"{(s.opening_amount or Decimal('0.00')):.2f}",
                f"{(s.total_sales or Decimal('0.00')):.2f}",
                f"{(s.total_expense or Decimal('0.00')):.2f}",
                f"{(s.total_difference or Decimal('0.00')):.2f}",
            ])

        resp = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename=\"reporte_caja_{start_date}_{end_date}.csv\"'
        return resp

    # Paginación
    page = request.GET.get("page", 1)
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(page)

    preserved = request.GET.copy()
    preserved.pop("page", None)
    qs_params = preserved.urlencode()

    context = {
        "page_obj": page_obj,
        "agg_total_sales":   f"{agg_total_sales:.2f}",
        "agg_total_expense": f"{agg_total_expense:.2f}",
        "agg_total_difference": f"{agg_total_difference:.2f}",
        "agg_sales_count":   agg_sales_count,
        "session_count": session_count,

        "start_date": start_date.strftime("%Y-%m-%d") if start_date else "",
        "end_date":   end_date.strftime("%Y-%m-%d") if end_date else "",
        "cashiers": User.objects.filter(Q(is_active=True) | Q(is_active=1)).order_by("username").distinct(),
        "cashier_selected": cashier_id,
        "qs_params": qs_params,
    }
    return render(request, "cash_report.html", context)

#REPORTE DE INVENTARIO
@login_required
@has_role("ADMINISTRADOR", "AUDITOR")
def inventory_report_view(request):
    year = request.GET.get("year")
    periodicity = request.GET.get("periodicity", "T")
    location_id = request.GET.get("location") or ""
    product_id = request.GET.get("product") or ""
    action = request.GET.get("action", "filter")
    export_format = (request.GET.get("export") or "").lower()

    # Año
    try:
        year = int(year)
    except (TypeError, ValueError):
        year = date.today().year

    # Filtros seleccionados
    location = Location.objects.filter(id_location=location_id).first() if location_id else None
    product = Product.objects.filter(id_product=product_id).first() if product_id else None

    # Query base
    qs = (InventoryMovement.objects
          .select_related("product", "location")
          .filter(fecha__year=year))
    if location:
        qs = qs.filter(location=location)
    if product:
        qs = qs.filter(product=product)
    qs = qs.order_by("product_id", "location_id", "fecha")

    # Periodos
    if periodicity == "T":
        periods = [("T1", (1, 3)), ("T2", (4, 6)), ("T3", (7, 9)), ("T4", (10, 12))]
    elif periodicity == "C":
        periods = [("C1", (1, 4)), ("C2", (5, 8)), ("C3", (9, 12))]
    else:
        periods = [("Año", (1, 12))]

    # Productos/Ubicaciones con movimientos (fallback si vacío)
    productos = Product.objects.filter(id_product__in=qs.values_list("product_id", flat=True).distinct())
    ubicaciones = Location.objects.filter(id_location__in=qs.values_list("location_id", flat=True).distinct())
    if not productos.exists():
        productos = Product.objects.all() if not product else [product]
    if not ubicaciones.exists():
        ubicaciones = Location.objects.all() if not location else [location]

    # Construcción de filas
    rows = []
    for p in productos:
        for l in ubicaciones:
            for label, (m1, m2) in periods:
                movs = qs.filter(product=p, location=l, fecha__month__gte=m1, fecha__month__lte=m2)
                entradas = Decimal(sum(m.entrada_cantidad or 0 for m in movs))
                salidas  = Decimal(sum(m.salida_cantidad or 0 for m in movs))
                neto = entradas - salidas

                prev_movs = qs.filter(product=p, location=l, fecha__month__lt=m1)
                saldo_inicial = Decimal(sum((m.entrada_cantidad or 0) - (m.salida_cantidad or 0) for m in prev_movs))
                saldo_final = saldo_inicial + neto

                if entradas or salidas or saldo_inicial:
                    rows.append({
                        "period": label,
                        "product_code": getattr(p, "code", p.id_product),
                        "product_name": p.name,
                        "location_name": l.name,
                        "saldo_inicial": saldo_inicial,
                        "entradas": entradas,
                        "salidas": salidas,
                        "neto": neto,
                        "saldo_final": saldo_final,
                    })

    # --- SOLO exporta si el botón fue "Descargar" ---
    if action == "export":
        if export_format == "csv":
            return export_inventory_csv(rows, year, periodicity)
        if export_format == "pdf":
            return export_inventory_pdf(rows, year, periodicity)
        messages.error(request, "Selecciona un formato (CSV o PDF) para exportar.")

    # Render normal
    return render(request, "inventory_report.html", {
        "rows": rows,
        "year": year,
        "periodicity": periodicity,
        "locations": Location.objects.all(),
        "products": Product.objects.all(),
        "selected_location": location_id,
        "selected_product": product_id,
        "export": export_format,  # mantener selección en el UI
    })


def export_inventory_csv(rows, year, periodicity):
    buffer = StringIO()
    writer = csv.writer(buffer, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    # Encabezados
    writer.writerow([
        "Periodo",
        "Código Producto",
        "Producto",
        "Ubicación",
        "Saldo Inicial",
        "Entradas",
        "Salidas",
        "Neto",
        "Saldo Final",
    ])

    # Filas
    for r in rows:
        writer.writerow([
            r["period"],
            r["product_code"],
            r["product_name"],
            r["location_name"],
            f"{(r['saldo_inicial'] or Decimal('0.00')):.2f}",
            f"{(r['entradas'] or Decimal('0.00')):.2f}",
            f"{(r['salidas'] or Decimal('0.00')):.2f}",
            f"{(r['neto'] or Decimal('0.00')):.2f}",
            f"{(r['saldo_final'] or Decimal('0.00')):.2f}",
        ])

    # Respuesta
    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="reporte_inventario_{year}_{periodicity}.csv"'
    return response


def export_inventory_pdf(rows, year, periodicity):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    story = [Paragraph(f"Reporte de Inventario {year} - {periodicity}", styles["Title"]), Spacer(1, 10)]

    data = [["Periodo", "Código Producto", "Producto", "Ubicación", "Saldo Inicial", "Entradas", "Salidas", "Neto", "Saldo Final"]]
    for r in rows:
        data.append([
            r["period"], r["product_code"], r["product_name"], r["location_name"],
            f"{r['saldo_inicial']:.2f}", f"{r['entradas']:.2f}", f"{r['salidas']:.2f}",
            f"{r['neto']:.2f}", f"{r['saldo_final']:.2f}"
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
        ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(table)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename=\"reporte_inventario_{year}_{periodicity}.pdf\"'
    response.write(pdf)
    return response