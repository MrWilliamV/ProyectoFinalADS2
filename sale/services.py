# sale/services.py

from decimal import Decimal
from io import BytesIO
import os
from typing import List, Dict, Tuple

from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from CashRegister.models import CashSession, CashMovement
from inventory.models import Location, Inventory, InventoryMovement, LotStock, InventoryConfig
from product.models import Product



def get_store_location() -> Location | None:
    """
    Returns the default store location.

    :return: Location instance if found, otherwise None.
    """
    loc = Location.objects.filter(code__iexact="ST").first()
    if not loc:
        loc = Location.objects.filter(name__icontains="tienda").first()
    return loc


def find_product_by_code(code: str) -> Product | None:
    """
    Finds a product by primary key or by barcode (if the field exists).

    :param code: Product ID (PK as string) or barcode text.
    :return: Product instance if found, otherwise None.
    """
    product = Product.objects.filter(pk=code).first()
    if not product and hasattr(Product, "barcode"):
        product = Product.objects.filter(barcode__iexact=code).first()
    return product


def available_stock_nonexpired(product: Product, store: Location, on_date=None) -> Decimal:
    """
    Add available quantity for a product at a specific store,
    considering only non-expired lots.

    :param product: Product to check.
    :param store: Location where to check the stock.
    :param on_date: Date used to filter non-expired lots; today if None.
    :return: Decimal with the available quantity (0 if none).
    """
    if on_date is None:
        on_date = timezone.localdate()
    return (
        LotStock.objects
        .filter(location=store, lot__product=product, lot__expire_date__gte=on_date)
        .aggregate(q=Sum("quantity"))["q"] or Decimal("0")
    )


def price_from_inventory(product: Product, store: Location) -> float:
    """
    Gets the current average unit cost for a product at a store.

    :param product: Product to price.
    :param store: Location to look up its inventory.
    :return: float with the average unit cost; 0.0 if not available.
    """
    inv = Inventory.objects.filter(product=product, location=store).first()
    return float(inv.avg_unit_cost) if inv and inv.avg_unit_cost else 0.0


def current_qty_in_cart(cart: List[Dict], product: Product) -> int:
    """
    Returns the quantity of a product already present in the cart.

    :param cart: List of cart items (dicts with keys 'id', 'qty', 'price', 'subtotal').
    :param product: Product to check in the cart.
    :return: Integer quantity currently in the cart.
    """
    for item in cart:
        if item["id"] == product.id_product:
            return int(item["qty"])
    return 0


def add_or_increment_cart_item(cart: List[Dict], product: Product, qty_to_add: int, unit_price: float) -> None:
    """
    Adds a product into the cart or increases its quantity if already present.

    :param cart: Current cart list stored in session.
    :param product: Product to insert/increment.
    :param qty_to_add: Quantity to add.
    :param unit_price: Price to use for subtotal calculation.
    :return: None
    """
    for item in cart:
        if item["id"] == product.id_product:
            item["qty"] += qty_to_add
            item["subtotal"] = item["qty"] * item["price"]
            break
    else:
        cart.append({
            "id": product.id_product,
            "name": product.name,
            "price": unit_price,
            "qty": qty_to_add,
            "subtotal": unit_price * qty_to_add,
        })


def increment_cart_item(cart: List[Dict], id_product: int) -> None:
    """
    Increments by one the quantity of a product in the cart.

    :param cart: Current cart list.
    :param id_product: Product PK used inside the cart dicts.
    :return: None
    """
    for item in cart:
        if item["id"] == id_product:
            item["qty"] += 1
            item["subtotal"] = item["qty"] * item["price"]
            break


def decrement_cart_item(cart: List[Dict], id_product: int) -> None:
    """
    Decrements by one the quantity of a product in the cart.
    Removes the item if the result is <= 0.

    :param cart: Current cart list.
    :param id_product: Product PK used inside the cart dicts.
    :return: None
    """
    for item in cart:
        if item["id"] == id_product:
            item["qty"] -= 1
            if item["qty"] <= 0:
                cart.remove(item)
            else:
                item["subtotal"] = item["qty"] * item["price"]
            break


def remove_cart_item(cart: List[Dict], id_product: int) -> None:
    """
    Removes a product from the cart regardless of its current quantity.

    :param cart: Current cart list.
    :param id_product: Product PK used inside the cart dicts.
    :return: None
    """
    for item in cart:
        if item["id"] == id_product:
            cart.remove(item)
            break


def cart_total(cart: List[Dict]) -> Decimal:
    """
    Sums all item subtotals to produce the cart total.

    :param cart: List of cart items with 'subtotal' key.
    :return: Decimal with the total value (0 if empty).
    """
    return sum(Decimal(str(item.get("subtotal", 0))) for item in cart)


def parse_cash_received(raw: str) -> Decimal:
    """
    Safely parses a raw cash string into Decimal.

    :param raw: Raw input string from the request.
    :return: Decimal with parsed value; 0.00 if parsing fails.
    """
    try:
        return Decimal(raw)
    except Exception:
        return Decimal("0.00")



def require_active_period() -> InventoryConfig:
    """
    Ensures there is an active inventory period.

    :return: InventoryConfig instance of the active period.
    :raises: ValueError if no active period exists.
    """
    cfg = InventoryConfig.objects.filter(is_active=True).first()
    if not cfg:
        raise ValueError("There must be an active inventory period before making a sale.")
    return cfg


def require_open_cash_session(store: Location) -> CashSession:
    """
    Ensures there is an open cash session for the given store.

    :param store: Location where the cash session must be open.
    :return: CashSession instance (latest open).
    :raises: ValueError if there is no open session for that store.
    """
    session = CashSession.objects.filter(location=store, is_open=True).order_by('-opened_at').first()
    if not session:
        raise ValueError("You must open the cash register before recording sales.")
    return session


def verify_stock_per_item(cart: List[Dict], store: Location, on_date=None) -> None:
    """
    Verifies each cart item has enough non-expired stock in the store.

    :param cart: List of items (expects keys: 'id', 'qty').
    :param store: Location to check stock from.
    :param on_date: Date used to filter non-expired lots; today if None.
    :return: None
    :raises: ValueError if any item exceeds the available non-expired stock.
    """
    if on_date is None:
        on_date = timezone.localdate()

    for item in cart:
        product = get_object_or_404(Product, pk=item["id"])
        disponible = (
            LotStock.objects
            .select_for_update()
            .filter(location=store, lot__product=product, lot__expire_date__gte=on_date)
            .aggregate(q=Sum("quantity"))["q"] or Decimal("0")
        )
        if Decimal(item["qty"]) > disponible:
            raise ValueError(
                f"Insufficient stock in Store for {product.name}. "
                f"Available (non-expired): {disponible}"
            )


def consume_stock_and_register_movements(cart: List[Dict], store: Location, period: InventoryConfig) -> None:
    """
    Consumes lot quantities and updates inventory while creating SAL movements.

    :param cart: Items to sell; expects keys: 'id', 'qty'.
    :param store: Store location where the sale occurs.
    :param period: Active inventory period to bind movements.
    :return: None
    :raises: ValueError if some item cannot be fully satisfied from available lots.
    """
    today = timezone.localdate()

    for item in cart:
        product = get_object_or_404(Product, pk=item["id"])

        inv, _ = Inventory.objects.select_for_update().get_or_create(
            product=product,
            location=store,
            defaults={"quantity": Decimal("0"), "avg_unit_cost": Decimal("0")}
        )
        unit_cost = inv.avg_unit_cost
        qty_to_sell = Decimal(item["qty"])

        lotes_st = (
            LotStock.objects
            .select_for_update()
            .filter(location=store, lot__product=product, lot__expire_date__gte=today, quantity__gt=0)
            .select_related("lot")
            .order_by("lot__expire_date", "lot_id")
        )

        restante = qty_to_sell
        for ls in lotes_st:
            if restante <= 0:
                break

            tomar = min(ls.quantity, restante)

            # Decrease lot and inventory
            ls.quantity = ls.quantity - tomar
            ls.save(update_fields=["quantity"])

            inv.quantity = inv.quantity - tomar
            inv.save(update_fields=["quantity"])

            # Create SAL movement
            InventoryMovement.objects.create(
                fecha=timezone.now(),
                tipo_movimiento="SAL",
                descripcion="Venta al contado",
                valor_unitario=unit_cost,
                entrada_cantidad=Decimal("0"),
                entrada_valor=Decimal("0"),
                salida_cantidad=tomar,
                salida_valor=tomar * unit_cost,
                saldo_cantidad=inv.quantity,
                saldo_valor=inv.quantity * unit_cost,
                product=product,
                location=store,
                lot=ls.lot,
                unidad=getattr(product, "unidad", "UND"),
                period=period,
            )

            restante -= tomar

        if restante > 0:
            raise ValueError(f"Could not complete the sale of {product.name}. Missing: {restante}")


def register_cash_movements(session: CashSession, cash_received: Decimal, change: Decimal) -> None:
    """
    Registers cash movements (deposit and change if applies) in the cash session.

    :param session: Open CashSession instance.
    :param cash_received: Amount received from the customer.
    :param change: Change to give back (>= 0).
    :return: None
    """
    CashMovement.objects.create(
        session=session,
        mtype='DEPOSITO',
        amount=cash_received,
        description='Venta POS - Entrada cliente',
        created_at=timezone.now(),
    )
    if change > 0:
        CashMovement.objects.create(
            session=session,
            mtype='RETIRO',
            amount=change,
            description='Venta POS - Cambio entregado',
            created_at=timezone.now(),
        )

def build_invoice_pdf(invoice_number: str,
                      cart: List[Dict],
                      total: Decimal,
                      cash_received: Decimal,
                      change: Decimal) -> bytes:
    """
    Builds a PDF invoice and returns its raw bytes.

    :param invoice_number: Unique invoice identifier to display in the PDF.
    :param cart: Items (expects: 'name', 'qty', 'price', 'subtotal').
    :param total: Total amount of the sale.
    :param cash_received: Cash amount received from the customer.
    :param change: Change to return to the customer.
    :return: Bytes content representing the generated PDF.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    logo_path = os.path.join("HealthAndHouse/static", "img", "logo.png")
    y_pos = height - 80

    # Header & logo
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        c.drawImage(logo, 50, y_pos - 30, width=80, height=50, preserveAspectRatio=True, mask='auto')

    c.setFont("Helvetica-Bold", 16)
    c.drawString(150, y_pos, "Health & House")

    c.setFont("Helvetica", 10)
    c.drawString(150, y_pos - 15, "No. Factura: " + invoice_number)
    c.drawString(150, y_pos - 30, "Cliente: CF (Consumidor Final)")
    c.drawString(150, y_pos - 45, f"Fecha: {timezone.now().strftime('%d/%m/%Y %H:%M')}")

    c.line(50, y_pos - 55, width - 50, y_pos - 55)

    # Table header
    y = y_pos - 80
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, "Producto")
    c.drawString(280, y, "Cantidad")
    c.drawString(380, y, "Precio")
    c.drawString(480, y, "Subtotal")

    c.setFont("Helvetica", 10)
    y -= 20

    # Items
    for item in cart:
        if y < 100:
            c.showPage()
            y = height - 100
            c.setFont("Helvetica-Bold", 12)
            c.drawString(60, y, "Producto")
            c.drawString(280, y, "Cantidad")
            c.drawString(380, y, "Precio")
            c.drawString(480, y, "Subtotal")
            c.setFont("Helvetica", 10)
            y -= 20

        name = str(item["name"])[:35]
        qty = item["qty"]
        price = float(item["price"])
        subtotal = float(item["subtotal"])

        c.drawString(60, y, name)
        c.drawRightString(330, y, f"{qty}")
        c.drawRightString(430, y, f"Q {price:.2f}")
        c.drawRightString(530, y, f"Q {subtotal:.2f}")
        y -= 15

    c.line(50, y - 5, width - 50, y - 5)
    y -= 25

    # Totals
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(530, y, f"Total: Q {float(total):.2f}")
    y -= 18
    c.setFont("Helvetica", 11)
    c.drawRightString(530, y, f"Pago: Q {float(cash_received):.2f}")
    y -= 18
    c.drawRightString(530, y, f"Vuelto: Q {float(change):.2f}")

    # Footer
    c.setFont("Helvetica-Oblique", 11)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawCentredString(width / 2, 50, "Gracias por preferirnos. ¡Vuelva pronto!")

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def generate_invoice_number() -> str:
    """
    Generates a simple invoice number based on the current timestamp.

    :return: String with the generated invoice number (e.g., 'F20251031153022').
    """
    return timezone.now().strftime("F%Y%m%d%H%M%S")



def make_sale_transaction(cart: List[Dict],
                          store: Location,
                          cash_received_raw: str) -> Tuple[bytes, str, Decimal, Decimal]:
    """
    Performs the complete sale transaction:
    validates active period and cash session, verifies stock, consumes lots,
    registers cash movements, and generates the PDF invoice bytes.

    :param cart: Cart items (expects keys: 'id', 'qty', 'price', 'subtotal').
    :param store: Store Location where the sale is being made.
    :param cash_received_raw: Raw string with the cash amount received from customer.
    :return: Tuple like pdf_bytes, invoice_number, total, change.
    :raises: ValueError if there is no active period/session, insufficient stock,
             invalid totals, or insufficient cash received.
    """
    if not cart:
        raise ValueError("Cart is empty.")

    period = require_active_period()
    session = require_open_cash_session(store)

    # Work with a copy of the cart for the PDF
    cart_for_pdf = [dict(item) for item in cart]

    with transaction.atomic():
        #Verify stock per item (row-level locks)
        verify_stock_per_item(cart, store, on_date=timezone.localdate())

        #Consume lots and register SAL movements
        consume_stock_and_register_movements(cart, store, period)

        #Totals and cash handling
        total = cart_total(cart)
        if total <= 0:
            raise ValueError("Sale total must be greater than 0.")

        cash_received = parse_cash_received(cash_received_raw)
        if cash_received < total:
            raise ValueError(f"Insufficient cash received (Q {cash_received}). Total: Q {total}.")

        change = (cash_received - total).quantize(Decimal("0.01"))

        # Cash movements
        register_cash_movements(session, cash_received, change)

        #Build PDF
        invoice_number = generate_invoice_number()
        pdf_bytes = build_invoice_pdf(
            invoice_number=invoice_number,
            cart=cart_for_pdf,
            total=total,
            cash_received=cash_received,
            change=change
        )

    return pdf_bytes, invoice_number, total, change
