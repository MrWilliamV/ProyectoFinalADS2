# reports/services.py (encabezado correcto)
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.core.paginator import Paginator
from django.db.models import Q, Sum, F

from CashRegister.models import CashMovement
from inventory.models import Product, InventoryMovement, Location  # ajusta si Location está en otra app

# PDF (ReportLab)
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

def _parse_date(value: str | None, fallback: Optional[date] = None) -> Optional[date]:
    if not value:
        return fallback
    return datetime.strptime(value, "%Y-%m-%d").date()


def _month_range(year: int, month: int) -> Tuple[date, date]:

    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def _periodic_slices(year: int, periodicity: str) -> List[Tuple[str, date, date]]:

    periodicity = (periodicity or "monthly").lower()
    if periodicity == "yearly":
        return [(str(year), date(year, 1, 1), date(year, 12, 31))]
    if periodicity == "quarterly":
        quarters = [(1, "Q1"), (4, "Q2"), (7, "Q3"), (10, "Q4")]
        slices = []
        for start_month, qlabel in quarters:
            s, e = _month_range(year, start_month)
            # fin de trimestre: sumar 2 meses al final
            last_month = start_month + 2
            _, e = _month_range(year, last_month)
            slices.append((f"{qlabel} {year}", s, e))
        return slices
    if periodicity == "monthly":
        out = []
        for m in range(1, 13):
            s, e = _month_range(year, m)
            out.append((f"{year}-{m:02d}", s, e))
        return out
    raise ValueError("Unsupported periodicity (use 'monthly', 'quarterly' or 'yearly').")
    #Periodicity

def _as_decimal(val: Any) -> float:

    try:
        return float(val or 0)
    except Exception:
        return 0.0

def get_kardex_context(request) -> Dict[str, Any]:
    """
    Build the Kardex context for rendering of filters, rows, pagination.

    :param request: HttpRequest with optional GET params
    :return: dict context for render
    :raises: ValueError for invalid dates/filters.
    """

    if Product is None or InventoryMovement is None:
        return {
            "filters": {},
            "rows": [],
            "page_obj": None,
            "warning": "Inventory models not available. Adjust imports in services.py.",
        }

    period = request.GET.get("period", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    product_id = request.GET.get("product")
    location_id = request.GET.get("location")
    page = request.GET.get("page", "1")

    today = date.today()
    if period and period != "custom":
        try:
            y, m = period.split("-")
            start_date, end_date = _month_range(int(y), int(m))
        except Exception:
            raise ValueError("Invalid period format. Use YYYY-MM or 'custom'.")
    else:
        start_date = _parse_date(start, date(today.year, today.month, 1))
        end_date = _parse_date(end, today)
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date cannot be greater than end date.")

    qs = InventoryMovement.objects.all()

    if product_id:
        qs = qs.filter(product_id=product_id)

    if location_id:
        qs = qs.filter(location_id=location_id)

    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    qs = qs.select_related("product", "location").order_by("date", "id")

    balance_qty = 0.0
    balance_cost = 0.0
    rows: List[Dict[str, Any]] = []
    for mov in qs:
        qty_in = _as_decimal(getattr(mov, "qty_in", 0))
        qty_out = _as_decimal(getattr(mov, "qty_out", 0))
        unit_cost = _as_decimal(getattr(mov, "unit_cost", 0))
        value = unit_cost * (qty_in or qty_out)

        balance_qty += qty_in - qty_out
        balance_cost += (qty_in * unit_cost) - (qty_out * unit_cost)

        rows.append({
            "date": getattr(mov, "date", None),
            "ref": getattr(mov, "reference", ""),
            "detail": getattr(mov, "detail", ""),
            "product": getattr(getattr(mov, "product", None), "name", ""),
            "location": getattr(getattr(mov, "location", None), "name", ""),
            "qty_in": qty_in,
            "qty_out": qty_out,
            "unit_cost": unit_cost,
            "value": value,
            "balance_qty": balance_qty,
            "balance_cost": balance_cost,
        })

    paginator = Paginator(rows, 50)
    page_obj = paginator.get_page(page)

    context = {
        "filters": {
            "period": period,
            "start": start_date,
            "end": end_date,
            "product": product_id,
            "location": location_id,
        },
        "rows": page_obj.object_list,
        "page_obj": page_obj,
        "totals": {
            "balance_qty": balance_qty,
            "balance_cost": balance_cost,
        },
    }
    return context

def get_cash_report_result(request) -> Dict[str, Any]:
    """
    Return a render context or CSV export for cash report.

    :param request: HttpRequest with GET params (start_date, end_date, cashier, export, page).
    :return: dict with either  for rendering.
    :raises: ValueError for invalid dates/filters.
    """
    start_date = _parse_date(request.GET.get("start_date"))
    end_date = _parse_date(request.GET.get("end_date"))
    cashier = request.GET.get("cashier")
    do_export = request.GET.get("export")
    page = request.GET.get("page", "1")

    if start_date and end_date and start_date > end_date:
        raise ValueError("Start date cannot be greater than end date.")

    if CashMovement is None:
        base_context = {
            "filters": {"start_date": start_date, "end_date": end_date, "cashier": cashier},
            "rows": [],
            "totals": {"in": 0.0, "out": 0.0, "net": 0.0},
            "page_obj": None,
            "warning": "Cash models not available. Adjust imports in services.py.",
        }
        if do_export == "csv":
            csv_content = _build_csv_from_rows([], headers=["Date", "Cashier", "Type", "Amount", "Note"])
            return {"export": "csv", "content": csv_content, "filename": _csv_name("cash", start_date, end_date)}
        return {"export": None, "context": base_context}

    qs = CashMovement.objects.all().select_related("session", "user").order_by("date", "id")

    if start_date:
        qs = qs.filter(date__date__gte=start_date)
    if end_date:
        qs = qs.filter(date__date__lte=end_date)
    if cashier:
        # admite id o username
        qs = qs.filter(Q(user__username__icontains=cashier) | Q(user__id__icontains=cashier))

    rows = []
    total_in = 0.0
    total_out = 0.0

    for mov in qs:
        amount = _as_decimal(getattr(mov, "amount", 0))
        mtype = getattr(mov, "movement_type", "")
        if str(mtype).upper() == "IN":
            total_in += amount
        else:
            total_out += amount

        rows.append({
            "date": getattr(mov, "date", None),
            "cashier": getattr(getattr(mov, "user", None), "username", ""),
            "type": mtype,
            "amount": amount,
            "note": getattr(mov, "note", ""),
        })

    net = total_in - total_out

    # Export CSV si se solicita
    if do_export == "csv":
        headers = ["Date", "Cashier", "Type", "Amount", "Note"]
        csv_rows = [[r["date"], r["cashier"], r["type"], r["amount"], r["note"]] for r in rows]
        csv_content = _build_csv_from_rows(csv_rows, headers=headers)
        return {
            "export": "csv",
            "content": csv_content,
            "filename": _csv_name("cash", start_date, end_date),
        }

    paginator = Paginator(rows, 50)
    page_obj = paginator.get_page(page)

    context = {
        "filters": {"start_date": start_date, "end_date": end_date, "cashier": cashier},
        "rows": page_obj.object_list,
        "page_obj": page_obj,
        "totals": {"in": total_in, "out": total_out, "net": net},
    }
    return {"export": None, "context": context}

def get_inventory_report_result(request) -> Dict[str, Any]:
    """
    Return inventory summary by period.

    :param request: HttpRequest with GET params (year, periodicity, location, product, action, export).
    :return: dict for render or export
    :raises: ValueError when filters/periodicity are invalid.
    """
    year_str = request.GET.get("year")
    periodicity = request.GET.get("periodicity", "monthly")
    location_id = request.GET.get("location")
    product_id = request.GET.get("product")
    action = request.GET.get("action")
    export_format = request.GET.get("export")

    if not year_str or not year_str.isdigit():
        raise ValueError("Invalid or missing 'year' parameter.")
    year = int(year_str)

    slices = _periodic_slices(year, periodicity)

    if InventoryMovement is None:
        rows: List[Dict[str, Any]] = []
        context = {
            "filters": {"year": year, "periodicity": periodicity, "location": location_id, "product": product_id},
            "rows": rows,
            "warning": "Inventory models not available. Adjust imports in services.py.",
        }
        if action == "export" and export_format in ("csv", "pdf"):
            if export_format == "csv":
                filename, csv_content = build_inventory_csv(rows, year, periodicity)
                return {"action": "export", "export": "csv", "filename": filename, "content": csv_content}
            filename, pdf_bytes = build_inventory_pdf(rows, year, periodicity)
            return {"action": "export", "export": "pdf", "filename": filename, "content_bytes": pdf_bytes}
        return {"action": "filter", "export": "", "context": context}

    base_qs = InventoryMovement.objects.all()
    if product_id:
        base_qs = base_qs.filter(product_id=product_id)
    if location_id:
        base_qs = base_qs.filter(location_id=location_id)

    rows: List[Dict[str, Any]] = []
    for label, start_d, end_d in slices:
        qs = base_qs.filter(date__date__gte=start_d, date__date__lte=end_d)

        qty_in = qs.aggregate(v=Sum("qty_in"))["v"] or 0
        qty_out = qs.aggregate(v=Sum("qty_out"))["v"] or 0

        val_in = qs.aggregate(v=Sum(F("qty_in") * F("unit_cost")))["v"] or 0
        val_out = qs.aggregate(v=Sum(F("qty_out") * F("unit_cost")))["v"] or 0

        rows.append({
            "period": label,
            "start": start_d,
            "end": end_d,
            "qty_in": float(qty_in),
            "qty_out": float(qty_out),
            "net_qty": float(qty_in) - float(qty_out),
            "value_in": float(val_in),
            "value_out": float(val_out),
            "net_value": float(val_in) - float(val_out),
        })

    if action == "export" and export_format in ("csv", "pdf"):
        if export_format == "csv":
            filename, csv_content = build_inventory_csv(rows, year, periodicity)
            return {"action": "export", "export": "csv", "filename": filename, "content": csv_content}
        filename, pdf_bytes = build_inventory_pdf(rows, year, periodicity)
        return {"action": "export", "export": "pdf", "filename": filename, "content_bytes": pdf_bytes}

    context = {
        "filters": {"year": year, "periodicity": periodicity, "location": location_id, "product": product_id},
        "rows": rows,
        "totals": {
            "qty_in": sum(r["qty_in"] for r in rows),
            "qty_out": sum(r["qty_out"] for r in rows),
            "net_qty": sum(r["net_qty"] for r in rows),
            "value_in": sum(r["value_in"] for r in rows),
            "value_out": sum(r["value_out"] for r in rows),
            "net_value": sum(r["net_value"] for r in rows),
        },
    }
    return {"action": "filter", "export": "", "context": context}




def build_inventory_csv(rows: Iterable[Dict[str, Any]], year: int, periodicity: str) -> Tuple[str, str]:
    """
    Build CSV content for inventory summary rows.

    :param rows: iterable of dict rows as returned by get_inventory_report_result()
    :param year: report year
    :param periodicity: 'monthly' | 'quarterly' | 'yearly'
    :return: (filename, csv_content)
    :raises: -
    """
    headers = [
        "Period", "Start", "End",
        "Qty In", "Qty Out", "Net Qty",
        "Value In", "Value Out", "Net Value",
    ]
    data = [
        [
            r.get("period", ""),
            r.get("start", ""),
            r.get("end", ""),
            r.get("qty_in", 0),
            r.get("qty_out", 0),
            r.get("net_qty", 0),
            r.get("value_in", 0),
            r.get("value_out", 0),
            r.get("net_value", 0),
        ]
        for r in rows
    ]
    csv_content = _build_csv_from_rows(data, headers=headers)
    filename = f"inventory_{periodicity}_{year}.csv"
    return filename, csv_content


def build_inventory_pdf(rows: Iterable[Dict[str, Any]], year: int, periodicity: str) -> Tuple[str, bytes]:
    """
    Build PDF bytes for inventory summary rows (simple tabular layout).

    :param rows: iterable of dict rows
    :param year: report year
    :param periodicity: 'monthly' | 'quarterly' | 'yearly'
    :return: filename, pdf
    """
    if canvas is None or LETTER is None:
        raise ValueError("ReportLab is required to generate PDF. Install reportlab package.")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)

    width, height = LETTER
    x = inch * 0.75
    y = height - inch * 1.0

    # Título
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, f"Inventory report - {periodicity.capitalize()} {year}")
    y -= 18

    # Encabezados
    headers = ["Period", "Start", "End", "Qty In", "Qty Out", "Net Qty", "Value In", "Value Out", "Net Value"]
    c.setFont("Helvetica-Bold", 9)
    y -= 6
    _draw_pdf_row(c, x, y, headers)
    y -= 14
    c.setFont("Helvetica", 9)

    # Filas
    for r in rows:
        _draw_pdf_row(
            c,
            x,
            y,
            [
                str(r.get("period", "")),
                str(r.get("start", "")),
                str(r.get("end", "")),
                f'{r.get("qty_in", 0):.2f}',
                f'{r.get("qty_out", 0):.2f}',
                f'{r.get("net_qty", 0):.2f}',
                f'{r.get("value_in", 0):.2f}',
                f'{r.get("value_out", 0):.2f}',
                f'{r.get("net_value", 0):.2f}',
            ],
        )
        y -= 14
        if y < inch:  # nueva página
            c.showPage()
            y = height - inch

    c.showPage()
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"inventory_{periodicity}_{year}.pdf"
    return filename, pdf_bytes


def _draw_pdf_row(c, x: float, y: float, cells: List[str], col_widths: Optional[List[int]] = None) -> None:
    """
    draw a single row of text cells in the PDF.

    :param c: reportlab canvas
    :param x: start x
    :param y: baseline y
    :param cells: list of strings
    :param col_widths: optional custom widths
    :return: None
    :raises: -
    """
    if col_widths is None:
        col_widths = [90, 65, 65, 55, 55, 55, 65, 65, 70]
    cx = x
    for i, text in enumerate(cells):
        c.drawString(cx, y, str(text))
        cx += col_widths[i] if i < len(col_widths) else 60

def _build_csv_from_rows(rows: Iterable[Iterable[Any]], headers: Optional[List[str]] = None) -> str:
    """
    Internal: build CSV string in-memory.

    :param rows: iterable of row iterables
    :param headers: optional header list
    :return: CSV content as string
    :raises: -
    """
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    if headers:
        writer.writerow(headers)
    for r in rows:
        writer.writerow(r)
    return output.getvalue()


def _csv_name(prefix: str, start_d: Optional[date], end_d: Optional[date]) -> str:
    """
    make a date ranged filename.

    :param prefix: file prefix
    :param start_d: start date
    :param end_d: end date
    :return: filename string
    """
    s = start_d.isoformat() if start_d else "NA"
    e = end_d.isoformat() if end_d else "NA"
    return f"{prefix}_{s}_{e}.csv"
