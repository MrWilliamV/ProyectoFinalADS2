from django.urls import path
from . import views

urlpatterns = [
    path('in', views.inventory_movement_view, name="inventory"),
    path('see', views.inventory_list_view , name="see_inventory"),
    path('transfer', views.traslado_lote_view, name="inventory_transfer"),
    path('initial_inventory', views.inventory_initial_import_view, name="initial_inventory"),
    path('initial/import/', views.inventory_initial_import_view, name="inventory_initial_import"),
    path("initial/", views.inventory_initial_hub, name="inventory_initial_hub"),

]