from django.db import models


class Proveedor(models.Model):
    """Tabla `proveedores` (RF-07, HU-11)."""

    id_proveedor = models.AutoField(primary_key=True)
    rut = models.CharField(max_length=12, unique=True)
    razon_social = models.CharField(max_length=120)
    contacto_nombre = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    correo = models.EmailField(max_length=100)
    dia_pedido = models.CharField(max_length=20, blank=True)
    dia_entrega = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "proveedores"

    def __str__(self):
        return self.razon_social