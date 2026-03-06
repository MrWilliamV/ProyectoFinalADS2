"""
Each route delegates logic to views.py, which in turn calls the corresponding
functions in services.py.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('kardex/', views.kardex_report, name='kardex'),
    path("reportes/caja/", views.cash_report, name="cash_report"),
    path('inventario/', views.inventory_report_view, name='inventory_report'),

]