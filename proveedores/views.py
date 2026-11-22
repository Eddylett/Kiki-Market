from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from usuarios.models import Rol
from usuarios.permisos import rol_requerido

from .forms import ProveedorForm
from .models import Proveedor


@rol_requerido(Rol.ADMINISTRADOR)
def proveedor_lista(request):
    proveedores = Proveedor.objects.annotate(num_productos=Count("productos")).order_by("razon_social")
    return render(request, "proveedores/proveedor_lista.html", {"proveedores": proveedores})


@rol_requerido(Rol.ADMINISTRADOR)
def proveedor_crear(request):
    form = ProveedorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Proveedor registrado.")
        return redirect("proveedor_lista")
    return render(request, "proveedores/proveedor_form.html", {"form": form, "titulo": "Nuevo proveedor"})


@rol_requerido(Rol.ADMINISTRADOR)
def proveedor_editar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    form = ProveedorForm(request.POST or None, instance=proveedor)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Proveedor actualizado.")
        return redirect("proveedor_lista")
    return render(request, "proveedores/proveedor_form.html", {"form": form, "titulo": "Editar proveedor"})