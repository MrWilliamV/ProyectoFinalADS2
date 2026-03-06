"""
This module defines all routes related to user operations:
listing users, creating new accounts, updating roles,
activating or deactivating users, and showing the user profile.
"""

from . import views
from django.urls import path

urlpatterns = [
    path('', views.users, name='users'),
    path('create/', views.create_user, name='create_user'),
    path('users/deactivate/<int:user_id>/<int:active>', views.is_active, name='is_active'),
    path('users/<int:user_id>/update_role/', views.update_user_role, name='update_user_role'),
    path("profile/", views.profile, name="profile"),

]
