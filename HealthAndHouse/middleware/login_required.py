import re
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

class LoginRequiredMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
        self.exempt_patterns = [re.compile(p) for p in getattr(settings, "LOGIN_EXEMPT_URLS", [])]
        self.static_prefixes = tuple(filter(None, [
            getattr(settings, "STATIC_URL", None),
            getattr(settings, "MEDIA_URL", None),
        ]))

    def process_request(self, request):
        path = request.path.lstrip("/")

        # Excluir static/media
        if any(path.startswith(p.lstrip("/")) for p in self.static_prefixes if p):
            return None

        # Excluir rutas publicas
        if any(p.match(path) for p in self.exempt_patterns):
            return None

        # Si esta autenticado, dejar pasar
        if request.user.is_authenticated:
            return None

        accepts = request.headers.get("Accept", "")
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        if "application/json" in accepts or is_ajax or path.startswith("api/"):
            return JsonResponse({"detail": "Authentication required"}, status=401)

        login_url = settings.LOGIN_URL
        return redirect(f"{login_url}?next={request.get_full_path()}")
