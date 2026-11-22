from django.urls import path

from . import views

urlpatterns = [
    path("pos/", views.pos, name="pos"),
    path("pos/agregar/", views.pos_agregar, name="pos_agregar"),
    path("pos/actualizar/<int:pk>/", views.pos_actualizar, name="pos_actualizar"),
    path("pos/quitar/<int:pk>/", views.pos_quitar, name="pos_quitar"),
    path("pos/confirmar/", views.pos_confirmar, name="pos_confirmar"),
    path("comprobante/<int:pk>/", views.comprobante, name="comprobante"),
    path("devolucion/<int:pk>/", views.devolucion_crear, name="devolucion_crear"),
    path("reportes/", views.reporte_cierre, name="reporte_cierre"),
    path("reportes/ventas/", views.reporte_ventas, name="reporte_ventas"),
    path("reportes/productos/", views.reporte_productos, name="reporte_productos"),
    path("reportes/categorias/", views.reporte_categorias, name="reporte_categorias"),
]