from django import forms
from django.utils import timezone

from .models import Categoria, ConfiguracionVencimiento, Lote, Merma, Producto


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "nombre", "categoria", "proveedor",
            "precio_costo", "precio_venta", "precio_oferta", "fin_oferta",
            "stock_estanteria", "stock_bodega", "stock_minimo",
        ]
        labels = {
            "nombre": "Nombre del producto",
            "categoria": "Categoría",
            "proveedor": "Proveedor",
            "precio_costo": "Precio de costo",
            "precio_venta": "Precio de venta",
            "precio_oferta": "Precio de oferta",
            "fin_oferta": "Fin de la oferta",
            "stock_estanteria": "Stock en estantería",
            "stock_bodega": "Stock en bodega",
            "stock_minimo": "Stock mínimo",
        }
        widgets = {"fin_oferta": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Categoria.objects.order_by("nombre")
        self.fields["categoria"].empty_label = "Selecciona una categoría"


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        # Los umbrales ya no se editan por categoría: se administran globalmente
        # desde la pantalla exclusiva del administrador.
        fields = ["nombre", "tipo"]
        labels = {
            "nombre": "Nombre de la categoría",
            "tipo": "Clasificación para vencimientos",
        }
        help_texts = {
            "nombre": "Puedes crear categorías como Bebidas, Lácteos, Aseo, Congelados, Panadería, etc.",
            "tipo": "Indica si el producto usa las alertas de perecibles o de despensa.",
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        duplicada = Categoria.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            duplicada = duplicada.exclude(pk=self.instance.pk)
        if duplicada.exists():
            raise forms.ValidationError("Ya existe una categoría con ese nombre.")
        return nombre

class ConfiguracionVencimientoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionVencimiento
        fields = ["perecible_aviso_1", "perecible_aviso_2", "perecible_aviso_3", "despensa_aviso"]
        labels = {
            "perecible_aviso_1": "Primer aviso preventivo (días)",
            "perecible_aviso_2": "Segundo aviso / prioridad alta (días)",
            "perecible_aviso_3": "Aviso urgente (días)",
            "despensa_aviso": "Aviso preventivo para despensa (días)",
        }
        help_texts = {
            "perecible_aviso_1": "Valor predeterminado: 15 días.",
            "perecible_aviso_2": "Valor predeterminado: 7 días.",
            "perecible_aviso_3": "Valor predeterminado: 3 días. Desde aquí el semáforo pasa a rojo.",
            "despensa_aviso": "Valor predeterminado: 30 días.",
        }
        widgets = {
            "perecible_aviso_1": forms.NumberInput(attrs={"min": 1, "max": 3650, "step": 1}),
            "perecible_aviso_2": forms.NumberInput(attrs={"min": 1, "max": 3650, "step": 1}),
            "perecible_aviso_3": forms.NumberInput(attrs={"min": 1, "max": 3650, "step": 1}),
            "despensa_aviso": forms.NumberInput(attrs={"min": 1, "max": 3650, "step": 1}),
        }

    def clean(self):
        datos = super().clean()
        aviso_1 = datos.get("perecible_aviso_1")
        aviso_2 = datos.get("perecible_aviso_2")
        aviso_3 = datos.get("perecible_aviso_3")
        despensa = datos.get("despensa_aviso")

        for campo in ("perecible_aviso_1", "perecible_aviso_2", "perecible_aviso_3", "despensa_aviso"):
            valor = datos.get(campo)
            if valor is not None and not 1 <= valor <= 3650:
                self.add_error(campo, "Ingresa un valor entre 1 y 3650 días.")

        if None not in (aviso_1, aviso_2) and aviso_1 <= aviso_2:
            self.add_error("perecible_aviso_1", "El primer aviso debe ser mayor que el segundo.")
        if None not in (aviso_2, aviso_3) and aviso_2 <= aviso_3:
            self.add_error("perecible_aviso_2", "El segundo aviso debe ser mayor que el aviso urgente.")
        if None not in (despensa, aviso_3) and despensa <= aviso_3:
            self.add_error("despensa_aviso", "El aviso de despensa debe ser mayor que el umbral urgente.")
        return datos


class RecepcionForm(forms.ModelForm):
    DESTINOS = [("estanteria", "Estantería"), ("bodega", "Bodega")]
    destino = forms.ChoiceField(choices=DESTINOS, label="Ubicación")

    class Meta:
        model = Lote
        fields = ["producto", "numero_lote", "fecha_vencimiento", "cantidad"]
        widgets = {"fecha_vencimiento": forms.DateInput(attrs={"type": "date"})}

    def clean_cantidad(self):
        cantidad = self.cleaned_data["cantidad"]
        if cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor que cero.")
        return cantidad

    def clean_fecha_vencimiento(self):
        fecha = self.cleaned_data["fecha_vencimiento"]
        if fecha < timezone.localdate():
            raise forms.ValidationError("La fecha de vencimiento no puede ser anterior a hoy.")
        return fecha


class MermaForm(forms.ModelForm):
    ORIGENES = [("estanteria", "Estantería"), ("bodega", "Bodega")]
    origen = forms.ChoiceField(choices=ORIGENES, label="Se retira de")

    class Meta:
        model = Merma
        fields = ["lote", "cantidad", "motivo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lote"].queryset = (
            Lote.objects.filter(cantidad__gt=0).select_related("producto").order_by("fecha_vencimiento")
        )

        self.fields["lote"].label_from_instance = (
            lambda l: f"{l.producto} · lote {l.numero_lote} ({l.cantidad} disponibles)"
        )

        

    def clean_cantidad(self):
        cantidad = self.cleaned_data["cantidad"]
        if cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor que cero.")
        return cantidad

    def clean(self):
        datos = super().clean()
        lote = datos.get("lote")
        cantidad = datos.get("cantidad")
        origen = datos.get("origen")
        if lote and cantidad:
            if cantidad > lote.cantidad:
                self.add_error("cantidad", f"El lote solo tiene {lote.cantidad} unidades.")
            elif origen:
                disponible = getattr(lote.producto, f"stock_{origen}")
                if cantidad > disponible:
                    self.add_error("cantidad", f"En {origen} solo hay {disponible} unidades de este producto.")
        return datos