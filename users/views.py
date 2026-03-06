"""
These views handle all actions related to users:
listing, creating, changing roles, activating/deactivating accounts,
and showing the current user's profile.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from HealthAndHouse.auth_rol import has_role
from . import services

ROLE_DESCRIPTIONS = {
    "ADMINISTRADOR": [
        "Puede acceder a todas las funcionalidades del sistema.",
        "Puede crear, editar y eliminar usuarios.",
        "Puede gestionar inventario, ventas y reportes.",
    ],
    "VENDEDOR": [
        "Puede realizar ventas y emitir facturas.",
        "Puede aperturar caja y registrar movimientos de efectivo.",
    ],
    "AUDITOR": [
        "Puede exportar reportes de caja, inventario y kardex.",
        "Tiene acceso de solo lectura a la información del sistema.",
    ],
    "JEFE_ALMACEN": [
        "Puede ver el inventario y realizar transferencias de stock.",
        "Puede registrar entradas por lote e inventario inicial (cuando hay período previo activo).",
        "Puede crear, editar o eliminar productos del catálogo.",
    ],
}

@login_required(login_url='login')
@has_role("ADMINISTRADOR")
def users(request):
    """
     This view shows active or inactive users depending on the
    filter chosen. It also ensures that the default system roles exist.

    :return: Rendered HTML page showing the user list with role information.
    """
    services.ensure_default_roles()

    status = request.GET.get("status", "active")
    users_qs = services.list_users_by_status(status=status)
    roles = services.list_roles()

    return render(request, "users.html", {
        "users": users_qs,
        "roles": roles,
        "status": status,
        "role_descriptions": ROLE_DESCRIPTIONS,
    })


@login_required(login_url='login')
@has_role("ADMINISTRADOR")
def update_user_role(request, user_id):
    """
    This view receives a POST request with the new role
    and updates the corresponding user.
    :param request: HTTP request object.
    :param user_id: ID of the user to update.

    :return:  Redirects back to the user list with a success or error message.
    """
    if request.method != 'POST':
        return redirect('users')

    role = (request.POST.get('role') or "").strip()
    try:
        services.set_user_single_role(user_id=user_id, role_name=role)
        user = get_object_or_404(User, pk=user_id)
        messages.success(request, f"Rol de {user.username} actualizado a {role}.")
    except services.RoleNotFound as e:
        messages.error(request, str(e))
    return redirect('users')


@login_required(login_url='login')
@has_role("ADMINISTRADOR")
def create_user(request):
    """
    This view handles user creation through a POST form.
    It delegates validation and creation logic to the service layer.
    :param request: HTTP request object.

    :return: Redirects back to the user list, showing a success or error message.
    """
    if request.method != 'POST':
        return redirect("users")

    first_name = request.POST.get('first_name') or ""
    last_name = request.POST.get('last_name') or ""
    email = request.POST.get('email') or ""
    username = request.POST.get('username') or ""
    password = request.POST.get('password') or ""
    role = (request.POST.get('role') or "").strip()

    try:
        services.create_user_with_role(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role_name=role if role else None,
        )
        messages.success(request, "El usuario se ha creado correctamente.")
    except services.UsernameTaken as e:
        messages.error(request, str(e))
    except services.RoleNotFound as e:
        messages.error(request, str(e))

    return redirect("users")


@login_required(login_url='login')
@has_role("ADMINISTRADOR")
def is_active(request, user_id, active):
    """

    This view changes a user's active state based on the value received
    in the URL. It converts the value to a boolean and calls the service layer.
    :param request: HTTP request object.
    :param user_id:  The ID of the user to update.
    :param active:  A string ('1', '0', 'true', 'false', etc.) indicating the new state.
    :return: Redirects to the user list after the change.
    """
    if request.method != 'POST':
        return redirect('users')

    # active te puede llegar como "0"/"1" o "true"/"false"
    raw = str(active).strip().lower()
    new_state = raw in ("1", "true", "t", "yes", "y")

    services.toggle_active(user_id=user_id, active=new_state)
    messages.success(request, "Usuario activado." if new_state else "Usuario desactivado.")
    return redirect('users')


@login_required()
def profile(request):
    """
    It shows basic information such as username, email, and
    the role assigned to the user.
    :param request: HTTP request object.
    :return: Rendered HTML page with user and role details.
    """
    user = request.user
    current_role = user.groups.first()
    return render(request, "profile.html", {
        "user": user,
        "role": current_role,
    })
