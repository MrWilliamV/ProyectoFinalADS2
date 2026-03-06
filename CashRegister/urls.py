from . import views
from django.urls import path

urlpatterns = [
    path('cash_register/', views.cash_register, name='cash_register'),
    #path('open/', views.cashbox_open, name='cashbox_open'),
    #path('status/', views.cashbox_status, name='cashbox_status'),
    #path('clsoe/', views.cashbox_close, name='cashbox_close'),
]