from django.views.decorators.http import require_POST

from HealthAndHouse.auth_rol import has_role
from inventory.models import Inventory, Location
from product.models import Product, Category, MeasureUnit, Brand

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .forms import ProductForm, MeasureUnitForm, CategoryForm, BrandForm
from inventory.services import initialize_inventory_for_product


@login_required(login_url='login')
@has_role("ADMINISTRADOR", "VENDEDOR", "JEFE_ALMACEN")
def product_list(request):
    """
       Renders the product list page with modals' forms.

       :param request: HttpRequest
       :return: HttpResponse rendering 'product.html'
       :raises: -
    """
    products = Product.objects.all()
    context = {
        "products": products,
        "form": ProductForm(),
        "brand_form": BrandForm(),
        "category_form": CategoryForm(),
        "measure_form": MeasureUnitForm(),
    }
    return render(request, 'product.html', context)


@login_required(login_url='login')
@has_role("ADMINISTRADOR", "JEFE_ALMACEN")
def form_create_product(request):
    """
        Shows the empty product creation form.

        :param request: HttpRequest
        :return: HttpResponse rendering 'create_product.html'
        :raises: -
    """

    form = ProductForm(request.POST)
    return render(request, 'create_product.html', {'form': form})

@login_required
@has_role("ADMINISTRADOR", "JEFE_ALMACEN")
def create_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Por favor corrige los campos marcados antes de continuar.")
            return render(request, "create_product.html", {"form": form})

        id_product = form.cleaned_data.get("id_product")

        if Product.objects.filter(pk=id_product).exists():
            messages.error(request, "Ya existe un producto con ese código de barras.")
            return render(request, "create_product.html", {"form": form})

        min_st = form.cleaned_data.get("min_st") or Decimal("0")
        max_st = form.cleaned_data.get("max_st") or Decimal("0")
        min_wh = form.cleaned_data.get("min_wh") or Decimal("0")
        max_wh = form.cleaned_data.get("max_wh") or Decimal("0")

        def pair_validate(min_v: Decimal, max_v: Decimal, etiqueta: str):
            if min_v <= 0:
                return f"{etiqueta}: el stock mínimo debe ser mayor que 0."
            if max_v <= 0:
                return f"{etiqueta}: el stock máximo debe ser mayor que 0."
            if max_v <= min_v:
                return f"{etiqueta}: el stock máximo debe ser mayor que el mínimo."
            return None

        err = pair_validate(min_st, max_st, "Tienda (ST)")
        if err:
            messages.error(request, err)
            return render(request, "create_product.html", {"form": form})

        err = pair_validate(min_wh, max_wh, "Bodega (WH)")
        if err:
            messages.error(request, err)
            return render(request, "create_product.html", {"form": form})

        try:
            with transaction.atomic():
                product = form.save()

                initialize_inventory_for_product(
                    product_id=product.id_product,
                    st_min=min_st,
                    st_max=max_st,
                    wh_min=min_wh,
                    wh_max=max_wh,
                )

            messages.success(request, "Producto creado y umbrales por bodega guardados correctamente.")
            return redirect("product_list")

        except Exception as e:
            messages.error(request, f"No se pudo crear el producto: {e}")
            return render(request, "create_product.html", {"form": form})

    else:
        form = ProductForm()

    return render(request, "create_product.html", {"form": form})

@require_POST
@login_required(login_url='login')
@has_role("ADMINISTRADOR", "JEFE_ALMACEN")
def delete_product(request, id_product):
    if request.method == "POST":
        product = get_object_or_404(Product, pk=id_product)
        product.delete()
    return redirect("product_list")


@login_required
@has_role("ADMINISTRADOR", "JEFE_ALMACEN", "VENDEDOR")
def product_detail(request, id_product):
    """
        Deletes a product, delegating persistence to services.

        :param request: HttpRequest
        :param id_product: Product PK to delete
        :return: HttpResponse redirect to 'product_list'
        :raises: ValueError if product does not exist or cannot be deleted.
    """
    product = get_object_or_404(Product, pk=id_product)
    editable = request.GET.get("edit") == "1"

    locations = list(Location.objects.filter(code__in=['ST', 'WH']))
    inventories = []
    with transaction.atomic():
        for loc in locations:
            inv, created = Inventory.objects.get_or_create(
                product=product, location=loc,
                defaults={
                    'quantity': Decimal('0.00'),
                    'avg_unit_cost': Decimal('0.0000'),
                    'updated_at': timezone.now(),
                }
            )

            if not created and not inv.updated_at:
                inv.updated_at = timezone.now()
                inv.save(update_fields=['updated_at'])
            inventories.append(inv)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if 'id_product' in form.fields:
            form.fields['id_product'].disabled = True

        try:
            with transaction.atomic():
                if editable:
                    if form.is_valid():
                        form.save()
                    else:
                        return render(request, "product_detail.html", {
                            "product": product,
                            "form": form,
                            "editable": editable,
                            "inventories": inventories,
                        })

                for inv in inventories:
                    min_key = f"min_{inv.pk}"
                    max_key = f"max_{inv.pk}"
                    min_val = request.POST.get(min_key, None)
                    max_val = request.POST.get(max_key, None)

                    changed = False
                    if min_val is not None and min_val != '':
                        inv.min_stock = Decimal(str(min_val))
                        changed = True
                    if max_val is not None and max_val != '':
                        inv.max_stock = Decimal(str(max_val))
                        changed = True
                    if changed:
                        inv.updated_at = timezone.now()
                        inv.save(update_fields=['min_stock', 'max_stock', 'updated_at'])

            messages.success(request, "Cambios guardados correctamente.")
            return redirect("product_detail", id_product=product.pk)

        except Exception as e:
            messages.error(request, f"No se pudo guardar: {e}")

    else:
        form = ProductForm(instance=product)

    # Si no está en modo edición, deshabilitar campos del producto
    if not editable:
        for f in form.fields.values():
            f.disabled = True

    return render(request, "product_detail.html", {
        "product": product,
        "form": form,
        "editable": editable,
        "inventories": inventories,
    })

@login_required()
@has_role("ADMINISTRADOR", "JEFE_ALMACEN")
def is_active_product(request, id_product, active):
    """
        Toggles the 'active' flag for a product.

        :param request: HttpRequest
        :param id_product: Product PK
        :param active: bool coercible (from path)
        :return: HttpResponse redirect to 'product_list'
        :raises: ValueError if product does not exist.
    """
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=id_product)
        product.active = active
        product.save()
    return redirect('product_list')

@login_required(login_url='login')
@require_POST
@transaction.atomic
@has_role("ADMINISTRADOR")
def create_brand(request):
    """
        Creates a Brand from modal and re-renders product list on errors.

        :param request: HttpRequest (POST with brand fields)
        :return: HttpResponse redirect to 'product_list' or render 'product.html' with modal open
        :raises: ValueError for invalid form data.
    """
    form = BrandForm(request.POST)

    if form.is_valid():
        form.save()
        messages.success(request, "Marca creada correctamente.")
        return redirect("product_list")

    # Reabrir modal con errores
    products = Product.objects.all().select_related("brand", "category", "measure_unit")
    context = {
        "products": products,
        "form": ProductForm(),
        "brand_form": form,
        "category_form": CategoryForm(),
        "measure_form": MeasureUnitForm(),
        "open_modal": "brand",
    }
    return render(request, "product.html", context)

@login_required()
@require_POST
@transaction.atomic
@has_role("ADMINISTRADOR")
def create_category(request):
    """
       Creates a Category from modal and re-renders product list on errors.

       :param request: HttpRequest (POST with category fields)
       :return: HttpResponse redirect to 'product_list' or render 'product.html' with modal open
       :raises: ValueError for invalid form data.
    """
    form = CategoryForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Categoría creada correctamente.")
        return redirect("product_list")

    products = Product.objects.all().select_related("brand", "category", "measure_unit")
    context = {
        "products": products,
        "form": ProductForm(),
        "brand_form": BrandForm(),
        "category_form": form,
        "measure_form": MeasureUnitForm(),
        "open_modal": "category",
    }
    return render(request, "product.html", context)

@login_required()
@require_POST
@transaction.atomic
@has_role("ADMINISTRADOR")
def create_measure(request):
    """
        Creates a MeasureUnit from modal and re-renders product list on errors.

        :param request: HttpRequest (POST with measure fields)
        :return: HttpResponse redirect to 'product_list' or render 'product.html' with modal open
        :raises: ValueError for invalid form data.
    """
    form = MeasureUnitForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Unidad de medida creada correctamente.")
        return redirect("product_list")

    products = Product.objects.all().select_related("brand", "category", "measure_unit")
    context = {
        "products": products,
        "form": ProductForm(),
        "brand_form": BrandForm(),
        "category_form": CategoryForm(),
        "measure_form": form,
        "open_modal": "measure",
    }
    return render(request, "product.html", context)
