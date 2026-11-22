from django.urls import path

from . import views

urlpatterns = [
    path("productos/", views.producto_lista, name="producto_lista"),
    path("productos/nuevo/", views.producto_crear, name="producto_crear"),
    path("productos/<int:pk>/editar/", views.producto_editar, name="producto_editar"),
    path("productos/<int:pk>/eliminar/", views.producto_eliminar, name="producto_eliminar"),
    path("recepcion/", views.recepcion_crear, name="recepcion_crear"),
    path("lotes/", views.lote_lista, name="lote_lista"),
    path("mermas/", views.merma_reporte, name="merma_reporte"),
    path("mermas/nueva/", views.merma_crear, name="merma_crear"),
]