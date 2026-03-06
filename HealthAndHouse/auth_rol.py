from django.contrib.auth.decorators import user_passes_test

from django.shortcuts import redirect
from django.contrib import messages

def has_role(*roles):
    """
    Decorator to restrict access to users belonging to specific roles (Django groups).

    This decorator checks whether the current user:
        1. Is authenticated.
        2. Is a superuser or belongs to any of the specified groups (roles).

    :param roles: One or more Django group names to authorize access.
    :return:
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                from django.conf import settings
                return redirect(settings.LOGIN_URL)
            if user.is_superuser or user.groups.filter(name__in=roles).exists():
                return view_func(request, *args, **kwargs)

            messages.warning(request, "No tienes permiso para acceder a esa sección.")
            return redirect(request.META.get("HTTP_REFERER", "/"))
        return _wrapped_view
    return decorator
