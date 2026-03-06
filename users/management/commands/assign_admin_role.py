import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = "Asigna el grupo ADMINISTRADOR al usuario admin (o al username indicado)"

    def handle(self, *args, **kwargs):
        User = get_user_model()
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise SystemExit(f"Usuario '{username}' no existe (crealo primero).")

        group, _ = Group.objects.get_or_create(name="ADMINISTRADOR")
        user.groups.add(group)

        self.stdout.write(self.style.SUCCESS(f"OK: {username} -> ADMINISTRADOR"))
