from django.urls import path

from . import views

urlpatterns = [
    path("proveedores/", views.proveedor_lista, name="proveedor_lista"),
    path("proveedores/nuevo/", views.proveedor_crear, name="proveedor_crear"),
    path("proveedores/<int:pk>/editar/", views.proveedor_editar, name="proveedor_editar"),
]