from django.core.management.base import BaseCommand
from supplier.models import Supplier


class Command(BaseCommand):
    help = "Crea un proveedor inicial"

    def handle(self, *args, **kwargs):
        supplier, created = Supplier.objects.get_or_create(
            name="Proveedor Genérico",
            defaults={
                "phone": "00000000",
                "email": "proveedor@demo.com",
                "address": "Ciudad",
                "nit": "CF",
                "contact_person": "Encargado General",
                "active": True,
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Proveedor creado: {supplier.name}")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"El proveedor ya existe: {supplier.name}")
            )