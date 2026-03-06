"""
This module contains helper functions that handle user creation,
role assignments, and account activation. These are used by the
views to keep the logic clean and organized.
"""
from typing import Iterable
from django.contrib.auth.models import User, Group
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.shortcuts import get_object_or_404


class UsernameTaken(Exception):
    """Raised when a username already exists."""
    pass


class RoleNotFound(Exception):
    """Raised when the specified role does not exist."""
    pass


def ensure_default_roles() -> None:
    """Raised when a username already exists."""
    for name in ["ADMINISTRADOR", "VENDEDOR", "AUDITOR", "JEFE_ALMACEN"]:
        Group.objects.get_or_create(name=name)


def list_users_by_status(*, status: str = "active") -> Iterable[User]:
    """
         Return users filtered by their active/inactive status.

    Args:
        status: 'active' or 'inactive'. Defaults to 'active'.

    Returns:
        A list of User objects.
    """
    is_active = (status == "active")
    return (
        User.objects.filter(is_active=is_active)
        .order_by("username")
        .prefetch_related("groups")
    )


def list_roles() -> Iterable[Group]:
    """
    :return:    Return all available roles in the system, ordered by name.
    """
    return Group.objects.all().order_by("name")


def _get_role_or_raise(role_name: str) -> Group:
    """
        Find a role by name or raise an error if it does not exist.

    :param role_name: Name of the role to search for.
    :return: a role name
    """
    role = Group.objects.filter(name=role_name).first()
    if not role:
        raise RoleNotFound(f"Rol '{role_name}' no existe.")
    return role


def assign_single_role(*, user: User, role_name: str) -> None:
    """
    :param user: The user instance to update.
    :param role_name: The name of the role to assign.

    :raises: RoleNotFound: If the role name does not exist.
    """
    if not role_name:
        raise RoleNotFound("Rol vacío o inválido.")
    role = _get_role_or_raise(role_name)
    user.groups.set([role])
    user.save(update_fields=["last_login"])


@transaction.atomic
def create_user_with_role(
        *, username: str, password: str,
        email: str = "", first_name: str = "", last_name: str = "",
        role_name: str | None = None
) -> User:
    """
    Create a new user and assign them a single role.

    :param username: The new username.
    :param password: The password in plain text (will be hashed with make_password).
    :param email:  Optional email address.
    :param first_name: Optional first name.
    :param last_name: Optional last name.
    :param role_name: Optional role to assign right after creation.
    :return:  The created User object.
    :raises:  UsernameTaken: If the username is already in use.
                RoleNotFound: If the role does not exist.
    """
    username = (username or "").strip()
    if not username:
        raise UsernameTaken("El nombre de usuario está vacío.")
    if User.objects.filter(username=username).exists():
        raise UsernameTaken("El nombre de usuario ya existe.")

    user = User.objects.create(
        username=username,
        first_name=(first_name or "").strip(),
        last_name=(last_name or "").strip(),
        email=(email or "").strip(),
        password=make_password(password or ""),
        is_staff=True,
        is_active=True,
    )

    if role_name:
        assign_single_role(user=user, role_name=role_name)

    return user


@transaction.atomic
def set_user_single_role(*, user_id: int, role_name: str) -> None:
    """
        Enable or disable a user account.

    :param user_id: ID of the user to update
    :param role_name:  True to activate, False to deactivate.
    :return: bool: The new active state of the user.
    """
    user = get_object_or_404(User, pk=user_id)
    assign_single_role(user=user, role_name=role_name)


@transaction.atomic
def toggle_active(*, user_id: int, active: bool) -> bool:
    """Activa/Desactiva un usuario y devuelve el nuevo estado."""
    user = get_object_or_404(User, pk=user_id)
    user.is_active = bool(active)
    user.save(update_fields=["is_active"])
    return user.is_active
