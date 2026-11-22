from django.contrib import admin

from .models import Categoria, Lote, Merma, Producto

admin.site.register(Categoria)
admin.site.register(Producto)
admin.site.register(Lote)
admin.site.register(Merma)