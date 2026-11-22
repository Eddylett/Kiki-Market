from django.db.models import F

from inventario.models import Producto
from usuarios.models import Rol


def alertas_stock(request):
    usuario = request.user
    if not usuario.is_authenticated or usuario.rol != Rol.ADMINISTRADOR:
        return {}
    criticos = (
        Producto.objects.annotate(total=F("stock_estanteria") + F("stock_bodega"))
        .filter(total__lte=F("stock_minimo"))
        .count()
    )
    return {"productos_criticos": criticos}