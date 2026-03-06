from django.urls import reverse, resolve, NoReverseMatch
from django.utils import timezone
from django.urls import resolve, reverse, NoReverseMatch


def sidebar_context(request):
    """
    Provides global sidebar navigation options for the entire application.

    :param request: HttpRequest instance.
    :return: dict containing a single key 'options' with sidebar definitions.
    """
    return {
        "options": [
            {
                "titulo": "Administrar usuarios",
                "url": "users",
                "icono": "M18 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0ZM3 19.235v-.11a6.375 6.375 0 0 1 12.75 0v.109A12.318 12.318 0 0 1 9.374 21c-2.331 0-4.512-.645-6.374-1.766Z"
            },
            {
                "titulo": "Catalogo de productos",
                "url": "product_list",
                "icono": "m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z"
            },
            {
                "titulo": "Realizar una venta",
                "url": "sales",
                "icono": "M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z"
            },

            {
                "titulo": "Inventario",
                "icono": "m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5m8.25 3v6.75m0 0-3-3m3 3 3-3M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z",
                "children": [
                    {
                        "titulo": "Entrada de inventario",
                        "url": "inventory",
                        "icono": "M12 6v12M6 12h12"
                    },
                    {"titulo": "Transferencias",
                     "url": "inventory_transfer",
                     "icono": "M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"},
                    {"titulo": "Ver inventario",
                     "url": "see_inventory",
                     "icono": "M2.25 12s3.75-6 9.75-6 9.75 6 9.75 6-3.75 6-9.75 6-9.75-6-9.75-6Z"},
                    {"titulo": "Inventario incial",
                     "url": "initial_inventory",
                     "icono": "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"},
                ],
            },
            {

                "titulo": "Caja",
                "url": "cash_register",
                "icono": "M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
            },
            {
                "titulo": "Reportes",
                "icono": "M10.125 2.25h-4.5c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125v-9M10.125 2.25h.375a9 9 0 0 1 9 9v.375M10.125 2.25A3.375 3.375 0 0 1 13.5 5.625v1.5c0 .621.504 1.125 1.125 1.125h1.5a3.375 3.375 0 0 1 3.375 3.375M9 15l2.25 2.25L15 12",
                "children": [
                    {"titulo": "Reporte de caja", "url": "cash_report",
                     "icono": "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z"},
                    {
                        "titulo": "Reporte de inventario",
                        "url": "inventory_report",
                        "icono": "M8.25 7.5V6.108c0-1.135.845-2.098 1.976-2.192.373-.03.748-.057 1.123-.08M15.75 18H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08M15.75 18.75v-1.875a3.375 3.375 0 0 0-3.375-3.375h-1.5a1.125 1.125 0 0 1-1.125-1.125v-1.5A3.375 3.375 0 0 0 6.375 7.5H5.25m11.9-3.664A2.251 2.251 0 0 0 15 2.25h-1.5a2.251 2.251 0 0 0-2.15 1.586m5.8 0c.065.21.1.433.1.664v.75h-6V4.5c0-.231.035-.454.1-.664M6.75 7.5H4.875c-.621 0-1.125.504-1.125 1.125v12c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V16.5a9 9 0 0 0-9-9Z"
                    },
                    {
                        "titulo": "Ver Kardex",
                        "icono": "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z",
                        "url": "kardex",
                    },
                ]

            },
            {
              "titulo": "Proveedores",
                "url": "list_suppliers",
                "icono": "M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z"
            },
        ]
    }


def breadcrumbs(request):

    """
        Builds a dynamic breadcrumb trail for the current page.

    :param request: HttpRequest instance.
    :return: dict with key 'crumbs', containing a list of breadcrumb dictionaries.
    """
    try:
        match = resolve(request.path_info)
        url_name = match.url_name or "dashboard"
        kwargs = match.kwargs or {}
    except Exception:
        url_name = "dashboard"
        kwargs = {}

    REG = {
        # Raíz/Dashboard
        "dashboard": {"label": "Panel", "parent": None},

        # Perfil
        "profile": {"label": "Perfil", "parent": "dashboard"},

        # Usuarios
        "users": {"label": "Usuarios", "parent": "dashboard"},
        "create_user": {"label": "Crear usuario", "parent": "users"},
        "delete_user": {
            "label": "Eliminar usuario",
            "parent": "users",
            "url_kwargs": lambda k: {"user_id": k.get("user_id")},
        },
        "is_active": {
            "label": "Activar/Desactivar usuario",
            "parent": "users",
            "url_kwargs": lambda k: {"user_id": k.get("user_id"), "active": k.get("active")},
        },

        # Productos
        "product_list": {"label": "Productos", "parent": "dashboard"},
        "form_create_product": {"label": "Nuevo producto (formulario)", "parent": "product_list"},
        "create_product": {"label": "Crear producto", "parent": "product_list"},
        "product_detail": {
            "label": "Detalle de producto",
            "parent": "product_list",
            "url_kwargs": lambda k: {"id_product": k.get("id_product")},
        },
        "is_active_product": {
            "label": "Activar/Desactivar producto",
            "parent": "product_list",
            "url_kwargs": lambda k: {"id_product": k.get("id_product"), "active": k.get("active")},
        },
        "remove_product": {
            "label": "Eliminar producto",
            "parent": "product_list",
            "url_kwargs": lambda k: {"id_product": k.get("id_product")},
        },

        # Ventas/Carrito
        "sales": {"label": "Ventas", "parent": "dashboard"},
        "add_product_by_barcode": {"label": "Carrito (agregar por código)", "parent": "sales"},
        "add_qty": {
            "label": "Aumentar cantidad",
            "parent": "sales",
            "url_kwargs": lambda k: {"id_product": k.get("id_product")},
        },
        "dec_qty": {
            "label": "Disminuir cantidad",
            "parent": "sales",
            "url_kwargs": lambda k: {"id_product": k.get("id_product")},
        },
        "remove_product_from_cart": {
            "label": "Quitar del carrito",
            "parent": "sales",
            "url_kwargs": lambda k: {"id_product": k.get("id_product")},
        },
        "make_a_sale": {"label": "Registrar venta", "parent": "sales"},

        # Inventario
        "inventory": {"label": "Inventario", "parent": "dashboard"},
        "see_inventory": {"label": "Existencias", "parent": "inventory"},
        "inventory_transfer": {"label": "Traslados de inventario", "parent": "inventory"},
        "initial_inventory": {"label": "Inventario inicial", "parent": "inventory"},

        # Reportes
        "reports": {"label": "reportes", "parent": "dashboard"},
        "cash_report": {"label": "reporte de caja", "parent": "dashboard"},
        "inventory_report": {"label": "reporte de inventario", "parent": "reports"},
        "kardex": {"label": "Ver kardex", "parent": "reports"},

        # Proveedores
        "list_suppliers": {"label": "proveedores", "parent": "dashboard"},
        "create_supplier": {"label": "crear proveedores", "parent": "list_suppliers"},

        # Caja
        "cash_register": {"label": "Caja", "parent": "dashboard"},
    }

    # Construcción de la cadena
    chain = []
    seen = set()
    cur = url_name
    for _ in range(50):
        if cur in seen:
            break
        seen.add(cur)
        chain.append(cur)
        spec = REG.get(cur)
        if not spec or not spec.get("parent"):
            break
        cur = spec["parent"]
    if not chain:
        chain = ["dashboard"]
    chain.reverse()

    # Construcción de crumbs
    crumbs = []
    for i, name in enumerate(chain):
        spec = REG.get(name, {})
        label = spec.get("label", name.replace("_", " ").title())

        if i == len(chain) - 1:
            url = None
        else:
            # Redirección explícita: "reportes" → cash_report
            if name == "reports":
                try:
                    url = reverse("cash_report")
                except NoReverseMatch:
                    url = None
            else:
                url_kwargs_fn = spec.get("url_kwargs")
                url_kwargs = url_kwargs_fn(kwargs) if url_kwargs_fn else {}
                try:
                    url = reverse(name, kwargs=url_kwargs or None)
                except NoReverseMatch:
                    url = None

        crumbs.append({"label": label, "url": url, "current": i == len(chain) - 1})

    return {"crumbs": crumbs}



def greeting(request):
    if not request.user.is_authenticated:
        return {}

    hour = timezone.localtime().hour
    print(f"[HORA {hour}")
    if 5 <= hour < 12:
        msg = f"Buenos días, {request.user.username}"
    elif 12 <= hour < 19:
        msg = f"Buenas tardes, {request.user.username}"
    else:
        msg = f"Buenas noches, {request.user.username}"
    return {"greeting": msg}
