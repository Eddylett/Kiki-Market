from django.conf import settings
from django.db import models
from django.utils import timezone


class MetodoPago(models.TextChoices):
    EFECTIVO = "efectivo", "Efectivo"
    DEBITO = "debito", "Débito"
    CREDITO = "credito", "Crédito"


class Venta(models.Model):
    id_venta = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="id_usuario",
        related_name="ventas",
    )
    nro_comprobante = models.CharField(max_length=30, unique=True)
    fecha_hora = models.DateTimeField(default=timezone.now)
    total_venta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    metodo_pago = models.CharField(max_length=30, choices=MetodoPago.choices, default=MetodoPago.EFECTIVO)

    class Meta:
        db_table = "ventas"

    def __str__(self):
        return f"Venta {self.nro_comprobante}"


class DetalleVenta(models.Model):
    id_detalle_venta = models.AutoField(primary_key=True, db_column="id_detalleVenta")
    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE, db_column="id_venta", related_name="detalles"
    )
    producto = models.ForeignKey(
        "inventario.Producto", on_delete=models.PROTECT, db_column="id_producto",
        related_name="detalles_venta",
    )
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "detalle_ventas"


class Devolucion(models.Model):
    id_devolucion = models.AutoField(primary_key=True)
    detalle_venta = models.ForeignKey(
        DetalleVenta, on_delete=models.PROTECT, db_column="id_detalleVenta",
        related_name="devoluciones",
    )
    fecha_hora = models.DateTimeField(default=timezone.now)
    cantidad = models.IntegerField()
    motivo = models.CharField(max_length=100)
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "devoluciones"