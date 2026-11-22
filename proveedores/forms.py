from django import forms

from .models import Proveedor


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "razon_social", "rut", "contacto_nombre", "telefono",
            "correo", "dia_pedido", "dia_entrega",
        ]
        labels = {
            "razon_social": "Razón social",
            "rut": "RUT",
            "contacto_nombre": "Nombre de contacto",
            "telefono": "Teléfono",
            "correo": "Correo (aquí llegan las órdenes de compra)",
            "dia_pedido": "Día de pedido",
            "dia_entrega": "Día de entrega",
        }
        widgets = {
            "rut": forms.TextInput(attrs={"placeholder": "12.345.678-9"}),
            "dia_pedido": forms.TextInput(attrs={"placeholder": "Ej: lunes"}),
            "dia_entrega": forms.TextInput(attrs={"placeholder": "Ej: miércoles"}),
        }

    def clean_rut(self):
        return self.cleaned_data["rut"].strip().upper()