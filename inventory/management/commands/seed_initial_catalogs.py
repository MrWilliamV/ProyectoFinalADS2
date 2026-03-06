from django.core.management.base import BaseCommand
from inventory.models import Location
from product.models import Brand, Category, MeasureUnit


class Command(BaseCommand):
    help = "Crea catálogos iniciales: Location, Brand, Category y MeasureUnit"

    def handle(self, *args, **kwargs):
        # Locations
        locations = [
            {"id_location": 1, "code": "WH", "name": "Bodega"},
            {"id_location": 2, "code": "ST", "name": "Tienda"},
        ]

        for item in locations:
            obj, created = Location.objects.get_or_create(
                code=item["code"],
                defaults={
                    "id_location": item["id_location"],
                    "name": item["name"],
                },
            )
            if not created:
                changed = False
                if obj.name != item["name"]:
                    obj.name = item["name"]
                    changed = True
                if changed:
                    obj.save()

        # Brand
        brands = [
            {"name": "Genérica", "description": "Marca inicial del sistema"},
        ]

        for item in brands:
            obj, created = Brand.objects.get_or_create(
                name=item["name"],
                defaults={"description": item["description"]},
            )
            if not created and obj.description != item["description"]:
                obj.description = item["description"]
                obj.save()

        # Category
        categories = [
            {
                "category_name": "General",
                "category_description": "Categoría inicial del sistema",
            },
        ]

        for item in categories:
            obj, created = Category.objects.get_or_create(
                category_name=item["category_name"],
                defaults={
                    "category_description": item["category_description"],
                },
            )
            if not created and obj.category_description != item["category_description"]:
                obj.category_description = item["category_description"]
                obj.save()

        # MeasureUnit
        units = [
            {"code": "UND", "name": "Unidad", "active": True},
        ]

        for item in units:
            obj, created = MeasureUnit.objects.get_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "active": item["active"],
                },
            )
            if not created:
                changed = False
                if obj.name != item["name"]:
                    obj.name = item["name"]
                    changed = True
                if obj.active != item["active"]:
                    obj.active = item["active"]
                    changed = True
                if changed:
                    obj.save()

        self.stdout.write(self.style.SUCCESS("OK: catálogos iniciales creados/actualizados"))