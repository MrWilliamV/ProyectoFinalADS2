from django.urls import path
from . import views

urlpatterns = [
    path('', views.sales, name='sales'),
    path('cart/', views.add_product_by_barcode, name='add_product_by_barcode'),
    path('add/<int:id_product>', views.add_qty, name='add_qty'),
    path('dec/<int:id_product>', views.dec_qty, name='dec_qty'),
    path('remove/<int:id_product>', views.remove_product_from_cart, name="remove_product_from_cart"),
    path('make_sale/', views.make_a_sale, name='make_a_sale'),
]
