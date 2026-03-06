from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', include('dashboard.urls')),
    path('', include('accounts.urls')),
    path('dashboard/users/', include('users.urls')),
    path('dashboard/product/', include('product.urls')),
    path('dashboard/sale', include('sale.urls')),
    path('dashboard/inventory', include('inventory.urls')),
    path('dashboard/cash_register', include('CashRegister.urls')),
    path('dashboard/reports', include('reports.urls')),
    path('dashboard/supplier', include('supplier.urls')),
]