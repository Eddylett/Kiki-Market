from django.urls import path

from . import views

urlpatterns = [
    path("reposicion/", views.reposicion, name="reposicion"),
    path("ordenes/", views.orden_lista, name="orden_lista"),
    path("ordenes/<int:pk>/", views.orden_detalle, name="orden_detalle"),
]