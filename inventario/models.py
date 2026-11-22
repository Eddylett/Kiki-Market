from django.db import models
from django.utils import timezone


class TipoProducto(models.TextChoices):
    PERECIBLE = "perecible", "Perecible"
    DESPENSA = "despensa", "De despensa"


class MotivoMerma(models.TextChoices):
    VENCIMIENTO = "vencimiento", "Vencimiento"
    CAMBIO_PROVEEDOR = "cambio_proveedor", "Cambio con el proveedor"
    CONSUMO_PROPIO = "consumo_propio", "Consumo propio"
    OTRO = "otro", "Otro"


class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=60)
    tipo = models.CharField(max_length=20, choices=TipoProducto.choices)
    dias_alerta = models.IntegerField(default=15)

    class Meta:
        db_table = "categorias"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    proveedor = models.ForeignKey(
        "proveedores.Proveedor", on_delete=models.PROTECT, db_column="id_proveedor",
        null=True, blank=True, related_name="productos",
    )
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, db_column="id_categoria", related_name="productos"
    )
    # Único (HU-05) y opcional: los productos a granel se buscan a mano (RF-10)
    codigo_barra = models.CharField(max_length=50, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=120)
    precio_costo = models.DecimalField(max_digits=12, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2)
    precio_oferta = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fin_oferta = models.DateField(null=True, blank=True)
    stock_estanteria = models.IntegerField(default=0)
    stock_bodega = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=0)

    class Meta:
        db_table = "productos"

    def __str__(self):
        return self.nombre

    def stock_total(self):
        return self.stock_estanteria + self.stock_bodega

    def esta_en_stock_critico(self):
        return self.stock_total() <= self.stock_minimo

    def precio_final(self):
        vigente = self.precio_oferta is not None and (
            self.fin_oferta is None or self.fin_oferta >= timezone.localdate()
        )
        return self.precio_oferta if vigente else self.precio_venta

    def calcular_margen(self):
        return self.precio_final() - self.precio_costo


class Lote(models.Model):
    id_lote = models.AutoField(primary_key=True)
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, db_column="id_producto", related_name="lotes"
    )
    numero_lote = models.CharField(max_length=30)
    fecha_vencimiento = models.DateField()
    cantidad = models.IntegerField()
    fecha_ingreso = models.DateField(default=timezone.localdate)

    class Meta:
        db_table = "lotes"

    def __str__(self):
        return f"{self.producto} · lote {self.numero_lote}"

    def dias_para_vencer(self):
        return (self.fecha_vencimiento - timezone.localdate()).days

    def estado_semaforo(self):
        dias = self.dias_para_vencer()
        if dias <= 3:
            return "rojo"
        if dias <= self.producto.categoria.dias_alerta:
            return "amarillo"
        return "verde"


class Merma(models.Model):
    id_merma = models.AutoField(primary_key=True)
    lote = models.ForeignKey(
        Lote, on_delete=models.PROTECT, db_column="id_lote", related_name="mermas"
    )
    fecha = models.DateField(default=timezone.localdate)
    cantidad = models.IntegerField()
    motivo = models.CharField(max_length=30, choices=MotivoMerma.choices)
    costo_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "mermas"

    def __str__(self):
        return f"Merma de {self.cantidad} × {self.lote.producto}"