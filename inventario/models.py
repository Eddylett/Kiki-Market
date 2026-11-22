import secrets

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


class ConfiguracionVencimiento(models.Model):
    """Umbrales globales de vencimiento; se administra solo desde el perfil administrador."""

    id_configuracion = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    perecible_aviso_1 = models.PositiveSmallIntegerField(default=15)
    perecible_aviso_2 = models.PositiveSmallIntegerField(default=7)
    perecible_aviso_3 = models.PositiveSmallIntegerField(default=3)
    despensa_aviso = models.PositiveSmallIntegerField(default=30)

    class Meta:
        db_table = "configuracion_vencimientos"
        verbose_name = "configuración de vencimientos"
        verbose_name_plural = "configuración de vencimientos"

    def __str__(self):
        return "Configuración de alertas de vencimiento"

    @classmethod
    def obtener(cls):
        """Devuelve la única configuración; crea los valores predeterminados si faltan."""
        configuracion, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "perecible_aviso_1": 15,
                "perecible_aviso_2": 7,
                "perecible_aviso_3": 3,
                "despensa_aviso": 30,
            },
        )
        return configuracion

    def save(self, *args, **kwargs):
        # La tabla representa una configuración global y solo puede tener la fila ID 1.
        self.pk = 1
        super().save(*args, **kwargs)


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
    # Se genera automáticamente un código numérico único al guardar productos nuevos.
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

    @staticmethod
    def generar_codigo_barra():
        """Genera un código interno numérico de 13 dígitos con dígito de control EAN-13."""
        for _ in range(100):
            # El prefijo 2 se reserva habitualmente para códigos de circulación interna.
            base = "2" + f"{secrets.randbelow(10**11):011d}"
            suma = sum(int(digito) * (1 if posicion % 2 == 0 else 3)
                       for posicion, digito in enumerate(base))
            control = (10 - (suma % 10)) % 10
            codigo = f"{base}{control}"
            if not Producto.objects.filter(codigo_barra=codigo).exists():
                return codigo
        raise RuntimeError("No fue posible generar un código de barras único.")

    def save(self, *args, **kwargs):
        codigo_generado = False
        if not self.codigo_barra:
            self.codigo_barra = self.generar_codigo_barra()
            codigo_generado = True

        # Asegura que el código recién asignado también se guarde cuando se usa update_fields.
        if codigo_generado and kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"codigo_barra"}

        super().save(*args, **kwargs)

    def stock_total(self):
        return self.stock_estanteria + self.stock_bodega

    def estado_vencimiento(self, configuracion=None):
        """Devuelve el estado de vencimiento más urgente de los lotes con stock."""
        configuracion = configuracion or ConfiguracionVencimiento.obtener()
        lotes = [lote for lote in self.lotes.all() if lote.cantidad > 0]
        lote = min(lotes, key=lambda item: item.fecha_vencimiento) if lotes else None
        if lote is None:
            return "sin_lote"

        dias = lote.dias_para_vencer()
        if dias < 0:
            return "vencido"
        if dias <= configuracion.perecible_aviso_3:
            return "rojo"

        limite = (
            configuracion.perecible_aviso_1
            if self.categoria.tipo == TipoProducto.PERECIBLE
            else configuracion.despensa_aviso
        )
        if dias <= limite:
            return "amarillo"
        return "verde"

    def dias_minimos_para_vencer(self):
        """Días restantes del lote con vencimiento más próximo que aún tiene stock."""
        lotes = [lote for lote in self.lotes.all() if lote.cantidad > 0]
        lote = min(lotes, key=lambda item: item.fecha_vencimiento) if lotes else None
        return lote.dias_para_vencer() if lote else None

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

    def estado_semaforo(self, configuracion=None):
        """Calcula el semáforo usando los umbrales globales vigentes."""
        configuracion = configuracion or ConfiguracionVencimiento.obtener()
        dias = self.dias_para_vencer()

        if dias <= configuracion.perecible_aviso_3:
            return "rojo"

        if self.producto.categoria.tipo == TipoProducto.PERECIBLE:
            limite_preventivo = configuracion.perecible_aviso_1
        else:
            limite_preventivo = configuracion.despensa_aviso

        if dias <= limite_preventivo:
            return "amarillo"
        return "verde"

    def mensaje_alerta(self, configuracion=None):
        """Devuelve el aviso que corresponde al lote, o una cadena vacía si está en verde."""
        configuracion = configuracion or ConfiguracionVencimiento.obtener()
        dias = self.dias_para_vencer()
        tipo = self.producto.categoria.tipo

        if dias < 0:
            return f"Producto vencido hace {abs(dias)} día(s). Retirar y registrar la merma si corresponde."
        if dias <= configuracion.perecible_aviso_3:
            return f"Alerta urgente: quedan {dias} día(s) para vencer. Revisar de inmediato."

        if tipo == TipoProducto.PERECIBLE:
            if dias <= configuracion.perecible_aviso_2:
                return f"Prioridad alta: quedan {dias} día(s) para vencer (umbral de {configuracion.perecible_aviso_2} días)."
            if dias <= configuracion.perecible_aviso_1:
                return f"Aviso preventivo: quedan {dias} día(s) para vencer (umbral de {configuracion.perecible_aviso_1} días)."
        elif dias <= configuracion.despensa_aviso:
            return f"Aviso preventivo: quedan {dias} día(s) para vencer (umbral de {configuracion.despensa_aviso} días)."

        return ""


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