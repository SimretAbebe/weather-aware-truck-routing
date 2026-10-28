from django.urls import path

from . import views

urlpatterns = [
    path("analyze", views.analyze),
    path("geocode", views.geocode),
    path("health", views.health),
]