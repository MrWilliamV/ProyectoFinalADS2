from django.contrib.auth.urls import path
from . import views
urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('create/', views.form_create_product, name='form_create_product'),
    path('create/new', views.create_product, name='create_product'),
    path('create/category/', views.create_category, name='create_category'),
    path('create/unit/', views.create_measure, name='create_measure'),
    path('create/brand/', views.create_brand, name='create_brand'),
    path('is_active/<int:id_product>/<int:active>', views.is_active_product, name='is_active_product'),
    path('product_detail/<int:id_product>', views.product_detail, name='product_detail'),
    path('<int:id_product>/delete/', views.delete_product, name='remove_product'),

]