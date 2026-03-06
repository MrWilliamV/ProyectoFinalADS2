# inventory/services.py
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from django.db import transaction
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.db.models import Sum, Subquery, OuterRef, Value, F, DecimalField

from .models import (
    InventoryConfig, Inventory, LotStock, ProductLot,
    InventoryPeriodSnapshot, InventoryPeriodSnapshotItem, InventoryMovement, TIPO_MOVIMIENTO_INICIAL, Location
)


@transaction.atomic
def close_period_snapshot(user, cfg_id):
    """
    Performs the real accounting closure of the active inventory period.

    :param user: User instance performing the closure.
    :param cfg_id: ID of the active InventoryConfig to close.
    :return: dict containing:
             - snapshot_id (int)
             - items (int): number of items in snapshot
             - cutoff_ts (datetime): closure timestamp
             - status ('ok')
    :raises: InventoryConfig.DoesNotExist if the active config does not exist.
    """
    cfg = InventoryConfig.objects.select_for_update().get(pk=cfg_id, is_active=True)

    tz = timezone.get_current_timezone()
    cutoff_dt = timezone.datetime(
        cfg.fecha_corte.year, cfg.fecha_corte.month, cfg.fecha_corte.day,
        23, 59, 59, tzinfo=tz
    )

    snap = InventoryPeriodSnapshot.objects.create(
        periodo=cfg,
        cutoff_ts=cutoff_dt,
        creado_por=user.id,
    )

    ZERO_QTY = Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=4))
    ZERO_VAL = Value(Decimal("0.0000"), output_field=DecimalField(max_digits=16, decimal_places=4))

    movs = (
        InventoryMovement.objects
        .filter(period=cfg)
        .values("product_id", "location_id", "lot_id")
        .annotate(
            entradas=Coalesce(Sum("entrada_cantidad"), ZERO_QTY),
            salidas=Coalesce(Sum("salida_cantidad"), ZERO_QTY),
            entrada_valor=Coalesce(Sum("entrada_valor"), ZERO_VAL),
            salida_valor=Coalesce(Sum("salida_valor"), ZERO_VAL),
        )
        .annotate(
            qty=F("entradas") - F("salidas"),
            total=F("entrada_valor") - F("salida_valor"),
        )
        .filter(qty__gt=0)
        .order_by("product_id", "location_id", "lot_id")
    )

    items = []
    for r in movs:
        qty = r["qty"]
        total = r["total"]
        unit_cost = (total / qty) if qty > 0 else Decimal("0.0000")

        items.append(InventoryPeriodSnapshotItem(
            snapshot=snap,
            id_product_id=r["product_id"],
            id_location_id=r["location_id"],
            id_lot_id=r["lot_id"],
            qty=qty,
            unit_cost=unit_cost,
            total_cost=total,
        ))

    if items:
        InventoryPeriodSnapshotItem.objects.bulk_create(items, batch_size=1000)

    cfg.is_active = False
    cfg.save(update_fields=["is_active"])

    return {
        "snapshot_id": snap.id,
        "items": len(items),
        "cutoff_ts": snap.cutoff_ts,
        "status": "ok",
    }


def _inicio_por_fecha_corte(fecha_corte):
    """
    Determines the start date for a new period based on the cutoff date.

    :param fecha_corte: datetime.date representing the cutoff date.
    :return: datetime.datetime start timestamp for the new period.
    """
    tz = timezone.get_current_timezone()
    if fecha_corte.month == 6:
        return timezone.datetime(fecha_corte.year, 1, 1, tzinfo=tz)
    return timezone.datetime(fecha_corte.year, 7, 1, tzinfo=tz)


@transaction.atomic
def aplicar_snapshot_al_periodo_activo(user, snapshot_id):
    """
    Applies an existing snapshot as the opening balance for the active period.

    :param user: User instance applying the snapshot.
    :param snapshot_id: ID of the InventoryPeriodSnapshot to apply.
    :return: dict with counts:
             - ini_movements: number of created INI movements
             - lot_items: number of lots reconstructed
             - products: number of product-location combinations
             - cleaned_lotstock: lots deleted from previous period
             - zeroed_inventory: inventories reset to zero
    :raises: InventoryConfig.DoesNotExist or InventoryPeriodSnapshot.DoesNotExist
    """
    periodo = InventoryConfig.objects.select_for_update().get(is_active=True)
    start_ts = _inicio_por_fecha_corte(periodo.fecha_corte)
    snap = InventoryPeriodSnapshot.objects.select_for_update().get(pk=snapshot_id)
    now = timezone.now()

    bulk_movs = []
    for it in InventoryPeriodSnapshotItem.objects.filter(snapshot=snap).iterator(chunk_size=1000):
        bulk_movs.append(InventoryMovement(
            fecha=start_ts,
            tipo_movimiento=TIPO_MOVIMIENTO_INICIAL,
            descripcion="Saldo inicial desde snapshot de cierre",
            valor_unitario=(it.unit_cost or Decimal("0")),
            entrada_cantidad=it.qty,
            entrada_valor=it.total_cost,
            salida_cantidad=Decimal("0"),
            salida_valor=Decimal("0"),
            saldo_cantidad=it.qty,
            saldo_valor=it.total_cost,
            product_id=it.id_product_id,
            location_id=it.id_location_id,
            lot_id=it.id_lot_id,
            period=periodo,
        ))
    if bulk_movs:
        InventoryMovement.objects.bulk_create(bulk_movs, batch_size=1000)

    qty_by_lot_loc = defaultdict(lambda: Decimal("0"))
    lotloc_keys_snapshot = set()
    for it in InventoryPeriodSnapshotItem.objects.filter(snapshot=snap).iterator(chunk_size=1000):
        key = (it.id_lot_id, it.id_location_id)
        lotloc_keys_snapshot.add(key)
        qty_by_lot_loc[key] += it.qty

    for (lot_id, loc_id), qty in qty_by_lot_loc.items():
        ls, _ = LotStock.objects.get_or_create(
            lot_id=lot_id, location_id=loc_id,
            defaults={"quantity": Decimal("0")}
        )
        ls.quantity = qty
        ls.save(update_fields=["quantity"])

    all_lotloc_current = set(LotStock.objects.values_list("lot_id", "location_id"))
    to_delete = list(all_lotloc_current - lotloc_keys_snapshot)
    if to_delete:
        from django.db.models import Q
        q = Q()
        for lot_id, loc_id in to_delete:
            q |= Q(lot_id=lot_id, location_id=loc_id)
        if q:
            LotStock.objects.filter(q).delete()

    prodloc_sum = defaultdict(lambda: Decimal("0"))
    prodloc_val = defaultdict(lambda: Decimal("0"))
    prodloc_keys_snapshot = set()

    for it in InventoryPeriodSnapshotItem.objects.filter(snapshot=snap).iterator(chunk_size=1000):
        key = (it.id_product_id, it.id_location_id)
        prodloc_keys_snapshot.add(key)
        prodloc_sum[key] += it.qty
        prodloc_val[key] += it.total_cost

    for (prod_id, loc_id), qty_sum in prodloc_sum.items():
        total_val = prodloc_val[(prod_id, loc_id)]
        avg = (total_val / qty_sum) if qty_sum else Decimal("0")
        inv, _ = Inventory.objects.get_or_create(
            product_id=prod_id, location_id=loc_id,
            defaults={"quantity": Decimal("0"), "avg_unit_cost": Decimal("0"), "updated_at": now}
        )
        inv.quantity = qty_sum
        inv.avg_unit_cost = avg
        inv.updated_at = now
        inv.save(update_fields=["quantity", "avg_unit_cost", "updated_at"])

    all_prodloc_current = set(Inventory.objects.values_list("product_id", "location_id"))
    to_zero = list(all_prodloc_current - prodloc_keys_snapshot)
    if to_zero:
        from django.db.models import Q
        q = Q()
        for prod_id, loc_id in to_zero:
            q |= Q(product_id=prod_id, location_id=loc_id)
        if q:
            Inventory.objects.filter(q).update(quantity=Decimal("0"), avg_unit_cost=Decimal("0"), updated_at=now)

    return {
        "ini_movements": len(bulk_movs),
        "lot_items": len(lotloc_keys_snapshot),
        "products": len(prodloc_keys_snapshot),
        "cleaned_lotstock": len(to_delete),
        "zeroed_inventory": len(to_zero),
    }


def get_active_period():
    """
    Retrieves the currently active inventory period.

    :return: InventoryConfig instance if active period exists, otherwise None.
    """
    return InventoryConfig.objects.filter(is_active=True).select_related("main_location").first()


def get_previous_period(current_cfg: InventoryConfig):
    """
    Retrieves the most recent closed inventory period, excluding the current one.

    :param current_cfg: The current InventoryConfig instance.
    :return: The last closed InventoryConfig or None.
    """
    return (InventoryConfig.objects
            .filter(is_active=False)
            .exclude(pk=current_cfg.pk)
            .order_by('-fecha_corte', '-id')
            .first())


@transaction.atomic
def construir_snapshot_desde_movimientos_periodo(user, prev_cfg: InventoryConfig) -> InventoryPeriodSnapshot | None:
    """
    Builds a snapshot from the previous period's movements if none exists.

    :param user: User performing the operation.
    :param prev_cfg: Previous InventoryConfig to analyze.
    :return: Created InventoryPeriodSnapshot instance, or None if no positive balances.
    :raises: ValueError for inconsistent or missing data.
    """
    if not prev_cfg:
        return None

    ZERO_QTY = Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=4))
    ZERO_VAL = Value(Decimal("0.0000"), output_field=DecimalField(max_digits=16, decimal_places=4))

    agg = (
        InventoryMovement.objects
        .filter(period=prev_cfg)
        .values("product_id", "location_id", "lot_id")
        .annotate(
            entradas=Coalesce(Sum("entrada_cantidad"), ZERO_QTY),
            salidas=Coalesce(Sum("salida_cantidad"), ZERO_QTY),
            entrada_valor=Coalesce(Sum("entrada_valor"), ZERO_VAL),
            salida_valor=Coalesce(Sum("salida_valor"), ZERO_VAL),
        )
        .annotate(
            qty=F("entradas") - F("salidas"),
            total=F("entrada_valor") - F("salida_valor"),
        )
        .filter(qty__gt=0)
        .order_by("product_id", "location_id", "lot_id")
    )

    if not agg.exists():
        return None

    tz = timezone.get_current_timezone()
    cutoff_dt = timezone.datetime(
        prev_cfg.fecha_corte.year, prev_cfg.fecha_corte.month, prev_cfg.fecha_corte.day,
        23, 59, 59, tzinfo=tz
    )

    snap = InventoryPeriodSnapshot.objects.create(
        periodo=prev_cfg,
        cutoff_ts=cutoff_dt,
        creado_por=user,
    )

    items = []
    for r in agg:
        qty = r["qty"]
        total = r["total"]
        unit_cost = (total / qty) if qty > 0 else Decimal("0.0000")
        items.append(InventoryPeriodSnapshotItem(
            snapshot=snap,
            id_product_id=r["product_id"],
            id_location_id=r["location_id"],
            id_lot_id=r["lot_id"],
            qty=qty,
            unit_cost=unit_cost,
            total_cost=total,
        ))
    InventoryPeriodSnapshotItem.objects.bulk_create(items, batch_size=1000)
    return snap

def _q2(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _q4(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def require_active_period() -> InventoryConfig:
    """
    Devuelve el periodo activo de inventario.
    Lanza error si no existe.
    """
    cfg = InventoryConfig.objects.filter(is_active=True).select_related("main_location").first()
    if not cfg:
        raise ValueError("Debe existir un periodo de inventario activo.")
    return cfg


def get_location_by_code(code: str) -> Location:
    """
    Busca una ubicación por código.
    """
    loc = Location.objects.filter(code__iexact=code).first()
    if not loc:
        raise ValueError(f"No existe la ubicación con código '{code}'.")
    return loc


def get_or_create_inventory(product_id: int, location_id: int) -> Inventory:
    """
    Obtiene o crea el saldo general de un producto por ubicación.
    """
    inv, _ = Inventory.objects.get_or_create(
        product_id=product_id,
        location_id=location_id,
        defaults={
            "quantity": Decimal("0.00"),
            "avg_unit_cost": Decimal("0.0000"),
            "min_stock": Decimal("0.00"),
            "max_stock": Decimal("0.00"),
            "updated_at": timezone.now(),
        },
    )

    if not inv.updated_at:
        inv.updated_at = timezone.now()
        inv.save(update_fields=["updated_at"])

    return inv

def get_available_stock_nonexpired(product_id: int, location_id: int, on_date=None) -> Decimal:
    """
    Suma el stock disponible no vencido por producto y ubicación.
    """
    if on_date is None:
        on_date = timezone.localdate()

    qty = (
        LotStock.objects
        .filter(
            location_id=location_id,
            lot__product_id=product_id,
            lot__expire_date__gte=on_date
        )
        .aggregate(total=Sum("quantity"))["total"]
        or Decimal("0")
    )
    return _q2(qty)


def initialize_inventory_for_product(
    *,
    product_id: int,
    st_min: Decimal,
    st_max: Decimal,
    wh_min: Decimal,
    wh_max: Decimal,
) -> dict:
    """
    Inicializa o actualiza los registros de inventario base para ST y WH.
    """
    st = get_location_by_code("ST")
    wh = get_location_by_code("WH")
    now = timezone.now()

    inv_st = get_or_create_inventory(product_id=product_id, location_id=st.id_location)
    inv_st.min_stock = _q2(st_min)
    inv_st.max_stock = _q2(st_max)
    inv_st.updated_at = now
    inv_st.save(update_fields=["min_stock", "max_stock", "updated_at"])

    inv_wh = get_or_create_inventory(product_id=product_id, location_id=wh.id_location)
    inv_wh.min_stock = _q2(wh_min)
    inv_wh.max_stock = _q2(wh_max)
    inv_wh.updated_at = now
    inv_wh.save(update_fields=["min_stock", "max_stock", "updated_at"])

    return {
        "status": "ok",
        "product_id": product_id,
        "st_inventory_id": inv_st.id_inventory,
        "wh_inventory_id": inv_wh.id_inventory,
    }

@transaction.atomic
def registrar_entrada_compra(
    *,
    user,
    product,
    location,
    quantity,
    unit_cost,
    lot_code,
    expire_date,
    supplier,
    description,
    movement_type="PUR",
):
    """
    Registra una entrada de inventario por compra y devuelve:
    - inventory actualizado
    - movement creado
    - period activo
    - lot usado/creado
    """
    cfg = InventoryConfig.objects.select_for_update().filter(is_active=True).first()
    if not cfg:
        raise ValueError("No hay periodo contable activo. Configúralo antes de operar.")

    now = timezone.now()

    lot, created = ProductLot.objects.select_for_update().get_or_create(
        product=product,
        lot_code=lot_code,
        defaults={"expire_date": expire_date},
    )

    if not created and expire_date and lot.expire_date != expire_date:
        lot.expire_date = expire_date
        lot.save(update_fields=["expire_date"])

    inv, _ = Inventory.objects.select_for_update().get_or_create(
        product=product,
        location=location,
        defaults={
            "quantity": Decimal("0.00"),
            "avg_unit_cost": Decimal("0.0000"),
            "updated_at": now,
            "min_stock": Decimal("0.00"),
            "max_stock": Decimal("0.00"),
        },
    )

    lot_stock, _ = LotStock.objects.select_for_update().get_or_create(
        lot=lot,
        location=location,
        defaults={"quantity": Decimal("0.00")},
    )
    lot_stock.quantity = quantity + (lot_stock.quantity or Decimal("0.00"))
    lot_stock.save(update_fields=["quantity"])

    qty_prev = inv.quantity or Decimal("0.00")
    qty_new = qty_prev + quantity
    prev_avg = inv.avg_unit_cost or Decimal("0.0000")

    entrada_valor = quantity * unit_cost
    total_prev_val = qty_prev * prev_avg
    total_new_val = total_prev_val + entrada_valor
    avg_new = (total_new_val / qty_new) if qty_new > 0 else prev_avg

    inv.quantity = qty_new
    inv.avg_unit_cost = avg_new
    inv.updated_at = now
    inv.save(update_fields=["quantity", "avg_unit_cost", "updated_at"])

    unit_code = getattr(getattr(product, "measure_unit", None), "code", None) or "UND"

    movement = InventoryMovement.objects.create(
        product=product,
        location=location,
        lot=lot,
        fecha=now,
        tipo_movimiento=movement_type,
        descripcion=description,
        valor_unitario=unit_cost,
        entrada_cantidad=quantity,
        entrada_valor=entrada_valor,
        salida_cantidad=Decimal("0.00"),
        salida_valor=Decimal("0.0000"),
        saldo_cantidad=qty_new,
        saldo_valor=qty_new * avg_new,
        proveedor=supplier,
        unidad=unit_code,
        created_by=(user if getattr(user, "is_authenticated", False) else None),
        period=cfg,
    )

    return {
        "inventory": inv,
        "movement": movement,
        "period": cfg,
        "lot": lot,
    }