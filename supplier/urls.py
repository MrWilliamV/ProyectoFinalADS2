"""
Supplier app URL routing.
"""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.list_suppliers, name='list_suppliers'),
    path('create', views.create_supplier, name='create_supplier'),
    path('detail/<int:pk>', views.supplier_detail, name='supplier_detail'),
    path('update/<int:pk>', views.supplier_update, name='update_supplier'),
    path('is_active/<int:pk>', views.is_active_supplier, name='active_supplier'),
]