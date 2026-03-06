from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from product.models import Product


class Location(models.Model):
    id_location = models.PositiveSmallIntegerField(
        primary_key=True, db_column="id_location"
    )

    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=30)

    class Meta:
        db_table = "location"


class ProductLot(models.Model):
    id_lot = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, db_column="id_product", on_delete=models.DO_NOTHING)
    lot_code = models.CharField(max_length=40)
    expire_date = models.DateField()

    class Meta:
        db_table = "product_lot"
        unique_together = (("product", "lot_code"),)


class Inventory(models.Model):
    id_inventory = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, db_column="id_product", on_delete=models.DO_NOTHING)
    location = models.ForeignKey(Location, db_column="id_location", on_delete=models.DO_NOTHING)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    avg_unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0.0000"))
    min_stock = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    max_stock = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "inventory"
        unique_together = (
            ("product", "location"),
        )
        permissions = [
            ("transfer_stock", "Puede realizar transferencias"),
            ("lot_entry", "Puede registrar entradas por lote"),
            ("initial_inventory", "Puede cargar inventario inicial"),
            ("export_kardex", "Puede exportar kardex"),
            ("export_inventory", "Puede exportar reporte de inventario"),
        ]


class LotStock(models.Model):
    id_lot_stock = models.BigAutoField(primary_key=True, db_column="id_lot_stock")
    lot = models.ForeignKey('ProductLot', db_column='id_lot', on_delete=models.DO_NOTHING)
    location = models.ForeignKey('Location', db_column='id_location', on_delete=models.DO_NOTHING)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        db_table = "lot_stock"
        constraints = [
            models.UniqueConstraint(fields=["lot", "location"], name="uk_lot_location"),
        ]


TIPO_MOVIMIENTO_INICIAL = "INI"


class InventoryConfig(models.Model):
    """
    Config general de inventario: fecha de corte y periodo fiscal.
    Unica fila activa (usa is_active=True).
    """
    FISCAL_SEMESTRAL = "S"
    FISCAL_PERIOD_CHOICES = [
        (FISCAL_SEMESTRAL, "Semestral (dos por año)"),
    ]

    descripcion = models.CharField(max_length=120, blank=True, default="")
    fecha_corte = models.DateField(help_text="Fecha de corte contable (punto de partida).")
    fiscal_period = models.CharField(max_length=1, choices=FISCAL_PERIOD_CHOICES, default=FISCAL_SEMESTRAL)
    main_location = models.ForeignKey("Location", on_delete=models.PROTECT, related_name="inventory_main",
                                      help_text="Único almacén donde se hará el inventario inicial.")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Configuración de Inventario"
        verbose_name_plural = "Configuraciones de Inventario"

    def __str__(self):
        return f"Config Inventario (corte: {self.fecha_corte}, periodo: {self.get_fiscal_period_display()})"


class InventoryMovement(models.Model):
    class MovementType(models.TextChoices):
        OPEN = "OPEN", "Apertura"
        PUR = "PUR", "Compra/Ingreso"
        TIN = "TIN", "Traslado Entrada"
        TOUT = "TOUT", "Traslado Salida"
        SAL = "SAL", "Venta/Salida"
        ADJIN = "ADJIN", "Ajuste Entrada"
        ADJOUT = "ADJOUT", "Ajuste Salida"
        INI = "INI", "Inventario incial"

    id_movement = models.BigAutoField(primary_key=True)

    # Relaciones (ajusta las rutas si Product/Location/ProductLot están en otra app)
    product = models.ForeignKey('product.Product', db_column='id_product', on_delete=models.DO_NOTHING)
    location = models.ForeignKey('Location', db_column='id_location', on_delete=models.DO_NOTHING)
    lot = models.ForeignKey('ProductLot', db_column='id_lot', on_delete=models.DO_NOTHING,
                            null=True, blank=True)

    # Usuario de la sesión de Django
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column='created_by',
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        related_name='inventory_movements',
    )

    # Campos visibles del Kardex
    fecha = models.DateTimeField()
    tipo_movimiento = models.CharField(max_length=6, choices=MovementType.choices)
    descripcion = models.CharField(max_length=200)
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=4)

    # Entradas / Salidas
    entrada_cantidad = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    entrada_valor = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0.0000"))
    salida_cantidad = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    salida_valor = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0.0000"))

    # Saldos
    saldo_cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_valor = models.DecimalField(max_digits=14, decimal_places=4)

    # Extras
    proveedor = models.ForeignKey(
        'supplier.Supplier',
        db_column='id_supplier',  # <- usa la columna que ya existe
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        related_name='inventory_movements',
        # si NO quieres crear la restricción FK en MySQL, añade:
        # db_constraint=False,
    )
    unidad = models.CharField(max_length=10, default="UND")

    period = models.ForeignKey(
        InventoryConfig,
        on_delete=models.PROTECT,
        db_column="period_id",
        related_name="movements",
        null=True, blank=True,
    )

    class Meta:
        db_table = "inventory_movement"
        indexes = [
            models.Index(fields=["period"]),
            models.Index(fields=["product", "location", "fecha"], name="ix_mov_prod_loc_fecha"),
            models.Index(fields=["tipo_movimiento"], name="ix_mov_tipo"),
            models.Index(fields=["lot"], name="ix_mov_lot"),
        ]

    def __str__(self):
        return f"[{self.fecha:%Y-%m-%d %H:%M}] {self.get_tipo_movimiento_display()} · {self.descripcion}"


class InventoryInitialBatch(models.Model):
    """
    Registro de cada importación de Inventario Inicial (auditoría).
    """
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file_name = models.CharField(max_length=200)
    total_items = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=250, blank=True, default="")

    def __str__(self):
        return f"Batch Inicial #{self.id} - {self.created_at:%Y-%m-%d} ({self.total_items} items)"


def validate_cutoff_for_movement(movement, config: InventoryConfig | None):
    if not config:
        return
    if movement.period_id and movement.period_id != config.id:
        raise ValidationError("El movimiento pertenece a un periodo distinto al activo.")

    if movement.tipo_movimiento == TIPO_MOVIMIENTO_INICIAL:
        if movement.fecha != config.fecha_corte:
            raise ValidationError("El movimiento INICIAL debe registrarse en la fecha de corte contable.")
    else:
        if movement.fecha < config.fecha_corte:
            raise ValidationError("No se permiten movimientos con fecha anterior a la fecha de corte contable.")


class InventoryPeriodSnapshot(models.Model):
    periodo = models.ForeignKey(
        InventoryConfig,
        on_delete=models.DO_NOTHING,
        db_column='periodo_id',
    )
    cutoff_ts = models.DateTimeField()
    creado_por = models.IntegerField(db_column='creado_por')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_period_snapshot'


class InventoryPeriodSnapshotItem(models.Model):
    snapshot = models.ForeignKey(
        InventoryPeriodSnapshot,
        on_delete=models.CASCADE,
        db_column='snapshot_id',
    )
    id_product = models.ForeignKey(
        Product,
        on_delete=models.DO_NOTHING,
        db_column='id_product',
    )
    id_location = models.ForeignKey(
        Location,
        on_delete=models.DO_NOTHING,
        db_column='id_location',
    )
    id_lot = models.ForeignKey(
        ProductLot,
        on_delete=models.DO_NOTHING,
        db_column='id_lot',
        null=True, blank=True,
    )
    qty = models.DecimalField(max_digits=14, decimal_places=4)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=6)
    total_cost = models.DecimalField(max_digits=16, decimal_places=4)
    expiry = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'inventory_period_snapshot_item'
