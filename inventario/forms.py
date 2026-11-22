from django import forms
from django.utils import timezone

from .models import Lote, Merma, Producto


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "nombre", "codigo_barra", "categoria", "proveedor",
            "precio_costo", "precio_venta", "precio_oferta", "fin_oferta",
            "stock_estanteria", "stock_bodega", "stock_minimo",
        ]
        widgets = {"fin_oferta": forms.DateInput(attrs={"type": "date"})}


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