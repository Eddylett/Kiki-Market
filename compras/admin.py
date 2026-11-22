from django.contrib import admin

from .models import AlertaStock, DetalleCompra, OrdenCompra

admin.site.register(AlertaStock)
admin.site.register(OrdenCompra)
admin.site.register(DetalleCompra)