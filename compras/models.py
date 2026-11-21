from django.conf import settings
from django.db import models
from django.utils import timezone


class EstadoOrden(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente de aprobación"
    APROBADA = "aprobada", "Aprobada"
    ENVIADA = "enviada", "Enviada al proveedor"
    RECHAZADA = "rechazada", "Rechazada"


class AlertaStock(models.Model):
    id_alerta = models.AutoField(primary_key=True)
    producto = models.ForeignKey(
        "inventario.Producto", on_delete=models.PROTECT, db_column="id_producto",
        related_name="alertas",
    )
    fecha_hora = models.DateTimeField(default=timezone.now)
    stock = models.IntegerField()
    atendida = models.BooleanField(default=False)

    class Meta:
        db_table = "alertas_stock"

    def __str__(self):
        return f"Alerta: {self.producto} ({self.stock})"


class OrdenCompra(models.Model):
    id_orden = models.AutoField(primary_key=True)
    # Se completa al aprobar: audita qué administrador aprobó la orden
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="id_usuario",
        null=True, blank=True, related_name="ordenes_aprobadas",
    )
    alerta = models.ForeignKey(
        AlertaStock, on_delete=models.PROTECT, db_column="id_alerta",
        null=True, blank=True, related_name="ordenes",
    )
    proveedor = models.ForeignKey(
        "proveedores.Proveedor", on_delete=models.PROTECT, db_column="id_proveedor",
        related_name="ordenes",
    )
    fecha_creacion = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=EstadoOrden.choices, default=EstadoOrden.PENDIENTE)
    total_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ordenes_compra"

    def __str__(self):
        return f"Orden #{self.pk} · {self.proveedor}"


class DetalleCompra(models.Model):
    id_detalle_compra = models.AutoField(primary_key=True, db_column="id_detalleCompra")
    orden = models.ForeignKey(
        OrdenCompra, on_delete=models.CASCADE, db_column="id_orden", related_name="detalles"
    )
    producto = models.ForeignKey(
        "inventario.Producto", on_delete=models.PROTECT, db_column="id_producto",
        related_name="detalles_compra",
    )
    cantidad_sugerida = models.IntegerField()
    cantidad_aprobada = models.IntegerField(null=True, blank=True)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "detalle_compras"