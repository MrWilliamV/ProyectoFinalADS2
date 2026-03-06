# products/models.py
from django.conf import settings
from django.db import models


class Brand(models.Model):
    """
        id_brand (AutoField): Primary key. Database column: 'id_brand'.
        name (CharField): Unique brand name (max 45 chars).
        description (CharField): Optional short description (max 45 chars).
    """
    id_brand = models.AutoField(primary_key=True, db_column="id_brand")
    name = models.CharField(max_length=45, unique=True)
    description = models.CharField(max_length=45, blank=True)

    class Meta:
        db_table = "brand"

    def __str__(self): return self.name


class Category(models.Model):
    """
    id_category (AutoField): Primary key. Database column: 'id_category'.
    category_name (CharField): Unique category name (max 45 chars).
    category_description (CharField): Optional short description (max 45 chars).

    """
    id_category = models.AutoField(primary_key=True, db_column="id_category")

    category_name = models.CharField(max_length=45, unique=True)
    category_description = models.CharField(max_length=45, blank=True)

    class Meta:
        db_table = "category"

    def __str__(self): return self.category_name


class MeasureUnit(models.Model):
    """
    id_meassure_unit (AutoField): Primary key. Database column: 'id_meassure_unit'.
    code (CharField): Unique short code (e.g., 'UN', 'BX') up to 10 chars.
    name (CharField): Descriptive unit name (e.g., 'Unidad', 'Caja').
    active (BooleanField): Whether the unit is available to use.
    """
    id_meassure_unit = models.AutoField(primary_key=True, db_column="id_meassure_unit")

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=30)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "meassure_unit"

    def __str__(self): return f"{self.code} - {self.name}"


class Product(models.Model):
    """
      id_product (IntegerField): Primary key (manual). DB column: 'id_product'.
        description (CharField): Short, user-facing description (max 50 chars).
        name (CharField): Internal/technical name (max 45 chars). DB column: 'name'.
        brand (FK → Brand): Product brand, PROTECT on delete. DB column: 'id_brand'.
        category (FK → Category): Product category, PROTECT on delete. DB column: 'id_category'.
        measure_unit (FK → MeasureUnit): Base unit, PROTECT on delete. DB column: 'id_meassure_unit'.
        on_quantity (PositiveIntegerField): Display/legacy quantity field (default 0).
        active (BooleanField): Whether the product can be sold/used.
        last_movement_at (DateTimeField): Auto-updated on save; used for recency/order.
        user (FK → AUTH_USER_MODEL): Optional creator/owner. DB column: 'id_user'.
    """
    # No es auto_increment
    id_product = models.IntegerField(primary_key=True, db_column="id_product", editable=True)
    description = models.CharField(max_length=50)
    name = models.CharField(max_length=45, db_column="name")

    brand = models.ForeignKey(Brand, on_delete=models.PROTECT,
                              db_column="id_brand", related_name="product")
    category = models.ForeignKey(Category, on_delete=models.PROTECT,
                                 db_column="id_category", related_name="product")
    measure_unit = models.ForeignKey(MeasureUnit, on_delete=models.PROTECT,
                                     db_column="id_meassure_unit", related_name="product")

    on_quantity = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    last_movement_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.SET_NULL, null=True, blank=True, db_column="id_user", to_field="id")

    class Meta:
        db_table = "product"

    def __str__(self): return self.description
