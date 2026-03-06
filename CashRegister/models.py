from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from inventory.models import Location



BLOCK_CHOICES = (('AM', '08:00–12:00'), ('PM', '13:00–18:00'))
CASH_MOVE_CHOICES = (
    ('APERTURA', 'Apertura'),
    ('VENTA EFECTIVO', 'Venta efectivo'),
    ('DEPOSITO', 'Deposito'),
    ('RETIRO', 'Retiro'),
    ('CIERRE', 'Cierre')
)


class CashSession(models.Model):
    """
     id_cash_session (BigAutoField): Primary key.
        location (FK to Location): The store or branch where the session takes place.
        cashier (FK to AUTH_USER_MODEL): The user responsible for the session.
        date (DateField): Date when the session was opened.
        block (CharField): Indicates the time slot (AM or PM).
        opened_at (DateTimeField): Exact timestamp when the session started.
        closed_at (DateTimeField): Optional closure timestamp.
        opening_amount (DecimalField): Amount of cash available at the start.
        expected_cash (DecimalField): Computed expected total after all operations.
        counted_cash (DecimalField): Amount physically counted at closure.
        difference (DecimalField): Difference between counted and expected cash.
        is_open (BooleanField): Whether the session is currently active.
        notes (CharField): Optional notes for additional remarks.
    """
    id_cash_session = models.BigAutoField(primary_key=True, db_column='id_cash_session')

    location = models.ForeignKey(
        Location, on_delete=models.PROTECT,
        db_column='id_location', related_name='cash_sessions'
    )
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        db_column='id_user', related_name='cash_sessions'
    )

    date = models.DateField(db_column='date')
    block = models.CharField(db_column='block', max_length=2, choices=BLOCK_CHOICES)
    opened_at = models.DateTimeField(db_column='opened_at', default=timezone.now)
    closed_at = models.DateTimeField(db_column='closed_at', null=True, blank=True)
    opening_amount = models.DecimalField(db_column='opening_amount', max_digits=12, decimal_places=2)
    expected_cash = models.DecimalField(db_column='expected_cash', max_digits=12, decimal_places=2)
    counted_cash = models.DecimalField(db_column='counted_cash', max_digits=12, decimal_places=2, null=True, blank=True)
    difference = models.DecimalField(db_column='difference', max_digits=12, decimal_places=2, null=True, blank=True)
    is_open = models.BooleanField(db_column='is_open', default=True)
    notes = models.CharField(db_column='notes', max_length=255, blank=True, default='')

    class Meta:
        db_table = 'cash_session'
        permissions = [
            ("open_cash", "Puede aperturar caja"),
            ("export_cash_report", "Puede exportar reporte de caja"),
        ]

    def __str__(self):
        return f"Caja {self.location} {self.date} {self.block} ({'ABIERTA' if self.is_open else 'CERRADA'})"


class CashMovement(models.Model):
    """
      id_cash_movement (BigAutoField): Primary key.
        session (FK to CashSession): The session to which this movement belongs.
        mtype (CharField): Movement type (choices defined in CASH_MOVE_CHOICES).
        amount (DecimalField): Monetary amount involved in the movement.
        created_at (DateTimeField): Timestamp when the record was created.
        description (CharField): Optional short explanation of the movement.
    """
    id_cash_movement = models.BigAutoField(primary_key=True, db_column='id_cash_movement')

    session = models.ForeignKey(
        CashSession, on_delete=models.CASCADE,
        db_column='id_cash_session', related_name='movements'
    )

    mtype = models.CharField(db_column='mtype', max_length=15, choices=CASH_MOVE_CHOICES)
    amount = models.DecimalField(db_column='amount', max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(db_column='created_at', default=timezone.now)
    description = models.CharField(db_column='description', max_length=255, blank=True, default='')

    class Meta:
        db_table = 'cash_movement'
