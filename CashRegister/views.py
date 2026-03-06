from datetime import time
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.utils import timezone

from CashRegister.models import CashSession, CashMovement
from HealthAndHouse.auth_rol import has_role
from inventory.models import Location

def _get_store_location():
    """
    Retrieves the store location with code 'ST'.
    :return: Location instance for store ('ST') or None if not found.
    """
    return Location.objects.filter(code__iexact='ST').first()


def _current_block(now=None):
    """
    Determines the current work block (AM/PM) based on the local time.

    :param now:  Optional datetime object; defaults to current local time.
    :return:'AM' or 'PM' depending on the current block.
    """
    now = now or timezone.localtime()
    t = now.time()
    if time(8, 0) <= t < time(12, 0):  return 'AM'
    if time(13, 0) <= t <= time(18, 0): return 'PM'
    return 'AM'


from decimal import Decimal


def _compute_expected(session):
    """
    add the expected cash balance for the current session.

    :param session: CashSession instance currently open.
    :return:  Decimal representing expected cash total.
    """
    if not session:
        return Decimal("0.00")
    ingresos = session.movements.filter(mtype__in=['APERTURA', 'DEPOSITO']) \
                   .aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
    egresos = session.movements.filter(mtype__in=['RETIRO']) \
                  .aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
    return (ingresos - egresos).quantize(Decimal('0.01'))


@login_required
@has_role("ADMINISTRADOR", "VENDEDOR")
def cash_register(request):
    """
    Manages the full cash register workflow, including opening, closing,
    deposits, and withdrawals for t he store session.
    :param request:HttpRequest with optional POST data.
    :return: HttpResponse rendering 'cash_register.html' or redirect to 'cash_register'.
    """
    store = _get_store_location()
    if not store:
        messages.error(request, "No se encontró la Tienda (ST).")
        return redirect("dashboard")  # ajusta si tienes otra ruta de fallback

    session = CashSession.objects.filter(location=store, is_open=True).order_by('-opened_at').first()

    if request.method == "POST":
        action = (request.POST.get("action") or "").lower()

        if action == "open":
            if session:
                messages.info(request, "Ya hay una caja abierta.")
                return redirect("cash_register")
            block = (request.POST.get("block") or "AM").upper()
            if block not in ("AM", "PM"):
                block = "AM"
            try:
                opening_amount = Decimal(request.POST.get("opening_amount") or "1000.00")
            except Exception:
                opening_amount = Decimal("1000.00")

            with transaction.atomic():
                session = CashSession.objects.create(
                    location=store,
                    cashier=request.user,
                    date=timezone.localdate(),
                    block=block,
                    opening_amount=opening_amount,
                    expected_cash=Decimal("0.00"),
                    is_open=True,
                    opened_at=timezone.now(),
                )
                CashMovement.objects.create(
                    session=session,
                    mtype='APERTURA',
                    amount=opening_amount,
                    description='Apertura',
                    created_at=timezone.now(),
                )
            messages.success(request,
                             f"Caja abierta ({'AM 08–12' if block == 'AM' else 'PM 13–18'}) con Q {opening_amount}.")
            return redirect("cash_register")

        if not session:
            messages.error(request, "No hay una caja abierta.")
            return redirect("cash_register")

        if action == "close":
            try:
                counted = Decimal(request.POST.get("counted_cash") or "0")
            except Exception:
                counted = Decimal("0")
            with transaction.atomic():
                expected = _compute_expected(session)
                diff = (counted - expected).quantize(Decimal('0.01'))
                session.expected_cash = expected
                session.counted_cash = counted
                session.difference = diff
                session.is_open = False
                session.closed_at = timezone.now()
                session.save(update_fields=['expected_cash', 'counted_cash', 'difference', 'is_open', 'closed_at'])
                CashMovement.objects.create(
                    session=session, mtype='CIERRE', amount=Decimal('0.00'),
                    description='Cierre', created_at=timezone.now()
                )
            messages.success(request, f"Caja cerrada. Esperado Q {expected}, contado Q {counted}, diferencia Q {diff}.")
            return redirect("cash_register")

        if action in ("deposit", "withdraw"):
            # Monto y descripción opcional
            try:
                amount = Decimal(request.POST.get("amount") or "0")
            except Exception:
                amount = Decimal("0")
            desc = (request.POST.get("description") or "").strip()
            if amount <= 0:
                messages.error(request, "El monto debe ser mayor que 0.")
                return redirect("cash_register")

            mtype = 'DEPOSITO' if action == "deposit" else 'RETIRO'
            with transaction.atomic():
                CashMovement.objects.create(
                    session=session, mtype=mtype, amount=amount,
                    description=desc or (mtype.title()), created_at=timezone.now()
                )
            messages.success(request, f"{mtype} registrado por Q {amount}.")
            return redirect("cash_register")

        messages.error(request, "Acción no reconocida.")
        return redirect("cash_register")

    expected = _compute_expected(session) if session else None
    movements = session.movements.order_by('-created_at')[:100] if session else []
    return render(request, "cash_register.html", {
        "session": session,
        "expected": expected,
        "movements": movements,
    })
