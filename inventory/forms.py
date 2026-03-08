# apps/inventory/forms.py
from datetime import date, timezone
from email.policy import default
from time import strftime

from django import forms
from decimal import Decimal

from supplier.models import Supplier
from .models import Location, Inventory, InventoryConfig
from product.models import Product, MeasureUnit

UNIDADES_CHOICES = [
    ("ML", "Mililitro"), ("MG", "Miligramo"),
    ("GR", "Gramo"), ("KG", "Kilogramo"), ("LT", "Litro"), ("CJ", "Caja"),
]

MOV_CHOICES = [
    ("PUR", "Entrada (Compra)"),
    ("ADJIN", "Entrada (Ajuste)"),
    ("SAL", "Salida"),
    ("ADJOUT", "Salida (Ajuste)"),
]

class InventoryMoveForm(forms.Form):
    """
    Formulario único para entradas y salidas de inventario.
    - Entradas: requieren lote, vencimiento, precio y proveedor.
    - Salidas: no requieren esos campos.
    """

    movement_type = forms.ChoiceField(
        choices=MOV_CHOICES,
        initial="PUR",
        widget=forms.HiddenInput(),
    )

    location = forms.ModelChoiceField(
        queryset=Location.objects.none(),
        label="Ubicación",
        required=True,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"})
    )

    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        label="Producto",
        required=True,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"})
    )

    lot_code = forms.CharField(
        max_length=40,
        label="Codigo de lote",
        required=False,
        widget=forms.TextInput(attrs={"class": "input input-bordered w-full"})
    )

    expire_date = forms.DateField(
        label="Fecha de vencimiento",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "input input-bordered w-full"})
    )

    quantity = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        label="Cantidad",
        widget=forms.NumberInput(attrs={"class": "input input-bordered w-full"})
    )

    unit_price_in = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
        label="Valor unitario",
        required=False,
        widget=forms.NumberInput(attrs={"class": "input input-bordered w-full"})
    )

    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all().order_by("name"),
        label="Proveedor",
        required=False,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"})
    )

    descripcion = forms.CharField(
        max_length=200,
        initial="Ingreso por compra",
        label="Descripción",
        required=True,
        widget=forms.TextInput(attrs={"class": "input input-bordered w-full"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["location"].queryset = Location.objects.all().order_by("name")
        self.fields["product"].queryset = (
            Product.objects
            .select_related("measure_unit")
            .order_by("name")
        )

        self.fields["expire_date"].widget.attrs["min"] = date.today().isoformat()

    def clean(self):
        data = super().clean()

        movement_type = data.get("movement_type")
        product = data.get("product")
        location = data.get("location")
        quantity = data.get("quantity")
        expire_date = data.get("expire_date")

        entradas = ["PUR", "ADJIN"]
        salidas = ["SAL", "ADJOUT"]

        if movement_type not in entradas + salidas:
            self.add_error("movement_type", "Tipo de movimiento inválido.")

        # =========================
        # VALIDACIONES DE ENTRADA
        # =========================
        if movement_type in entradas:
            if not data.get("unit_price_in"):
                self.add_error("unit_price_in", "Requerido para entradas.")
            if not data.get("expire_date"):
                self.add_error("expire_date", "Requerido para entradas.")
            if not data.get("lot_code"):
                self.add_error("lot_code", "Requerido para identificar el lote.")
            if not data.get("supplier"):
                self.add_error("supplier", "Selecciona un proveedor.")

            if expire_date and expire_date <= date.today():
                self.add_error(
                    "expire_date",
                    "La fecha de vencimiento debe ser mayor a la fecha actual."
                )

            if product and location and quantity:
                try:
                    inv = Inventory.objects.get(product=product, location=location)
                    max_stock = inv.max_stock or Decimal("0")
                    current = inv.quantity or Decimal("0")

                    if max_stock > 0 and current + quantity > max_stock:
                        remaining = max_stock - current
                        if remaining < 0:
                            remaining = Decimal("0.00")

                        self.add_error(
                            "quantity",
                            f"La entrada excede el máximo en {location.name}. "
                            f"Máximo: {max_stock}, actual: {current}. "
                            f"Puedes ingresar como mucho {remaining}."
                        )
                except Inventory.DoesNotExist:
                    pass

        # =========================
        # VALIDACIONES DE SALIDA
        # =========================
        if movement_type in salidas:
            if product and location and quantity:
                try:
                    inv = Inventory.objects.get(product=product, location=location)
                    current = inv.quantity or Decimal("0")

                    if quantity > current:
                        self.add_error(
                            "quantity",
                            f"Stock insuficiente en {location.name}. Disponible: {current}."
                        )
                except Inventory.DoesNotExist:
                    self.add_error(
                        "quantity",
                        f"No existe inventario registrado para {product} en {location}."
                    )

        return data

class LotTransferForm(forms.Form):
    """
    product (ModelChoiceField): Product to transfer.
        lot_code (CharField): Lot identifier to transfer.
        from_location (ModelChoiceField): Origin location.
        to_location (ModelChoiceField): Destination location.
        quantity (DecimalField): Quantity to transfer (min 0.01).
        unidad (ChoiceField): Unit of measure for the transfer.
        descripcion (CharField): Optional description of the transfer.

    """
    product = forms.ModelChoiceField(queryset=Product.objects.all().order_by("name"), label="Producto")
    lot_code = forms.CharField(max_length=40, label="Código de lote")
    from_location = forms.ModelChoiceField(queryset=Location.objects.all().order_by("id_location"), label="Desde")
    to_location = forms.ModelChoiceField(queryset=Location.objects.all().order_by("id_location"), label="Hacia")
    quantity = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"), label="Cantidad")
    unidad = forms.ChoiceField(
        choices=[("UND", "Unidad"), ("ML", "Mililitro"), ("MG", "Miligramo"), ("GR", "Gramo"), ("KG", "Kilogramo"),
                 ("LT", "Litro"), ("CJ", "Caja")], initial="UND", label="Unidad")
    descripcion = forms.CharField(max_length=200, required=False, initial="Traslado de bodega a tienda",
                                  label="Descripción")

    def clean(self):
        data = super().clean()
        if data.get("from_location") and data.get("to_location") and data["from_location"] == data["to_location"]:
            self.add_error("to_location", "La ubicación de destino debe ser distinta a la de origen.")
        return data


class InventoryInitialImportForm(forms.Form):
    """
      file (FileField): .xlsx file containing product rows.
        replace_existing (BooleanField): Replace previously loaded initial inventory.
    """
    file = forms.FileField(
        label="Archivo Excel (xlsx)",
        help_text="Debe contener columnas: codigo_producto, cantidad_inicial, costo_unitario (opcional: lote, vencimiento)."
    )
    replace_existing = forms.BooleanField(
        required=False,
        label="Reemplazar inventario inicial previo",
        help_text="Si ya cargaste un inventario inicial antes, marca esta opción para borrarlo y reemplazarlo."
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Sube un archivo .xlsx")
        if f.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Archivo demasiado grande (máx 5MB).")
        return f


class InventoryConfigForm(forms.ModelForm):
    """
     period (ChoiceField): Accounting half-year period (H1/H2).
        auto_detect (BooleanField): Auto-detect period from current date.
        main_location (ModelChoiceField): Main warehouse (typically code WH).
    """
    PERIOD_CHOICES = (
        ("H1", "Enero – Junio"),
        ("H2", "Julio – Diciembre"),
    )

    # Nuevo: selección de periodo y checkbox de autodetección
    period = forms.ChoiceField(
        choices=PERIOD_CHOICES,
        required=False,
        label="Periodo contable",
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )
    auto_detect = forms.BooleanField(
        required=False,
        label="Detectar periodo según fecha actual",
        widget=forms.CheckboxInput(attrs={"class": "checkbox"}),
    )

    # Ya no exponemos fecha_corte al usuario; la calculamos en save()
    main_location = forms.ModelChoiceField(
        queryset=Location.objects.none(),  # se rellena en __init__
        label="Bodega principal (WH)",
        empty_label="-- Seleccione bodega (WH) --",
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )

    class Meta:
        model = InventoryConfig
        fields = ["period", "auto_detect", "main_location"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar la(s) bodegas WH; ajusta si usas varios códigos
        self.fields["main_location"].queryset = Location.objects.filter(code__iexact="WH").order_by("name")
        self.fields["main_location"].label_from_instance = lambda o: f"{o.name} ({o.code})"

        # Estado interno para la fecha calculada
        self._fecha_corte = None

    def clean(self):
        cleaned = super().clean()
        auto = cleaned.get("auto_detect")
        per = cleaned.get("period")

        today = date.today()
        year = today.year

        # Determinar periodo
        if auto:
            # Detectar periodo por fecha actual
            per = "H1" if today.month <= 6 else "H2"
            cleaned["period"] = per  # para que se refleje en el template si re-renderiza
        else:
            # Selección manual obligatoria
            if not per:
                raise forms.ValidationError(
                    "Selecciona un periodo contable o marca la casilla de detección automática.")

        # Calcular fecha_corte como último día del periodo del año actual
        if per == "H1":
            self._fecha_corte = date(year, 6, 30)
        else:  # H2
            self._fecha_corte = date(year, 12, 31)

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        # fijar la fecha de corte calculada
        obj.fecha_corte = self._fecha_corte
        obj.is_active = True

        if commit:
            # Desactivar otras activas
            InventoryConfig.objects.filter(is_active=True).exclude(pk=obj.pk).update(is_active=False)
            obj.save()
        return obj
