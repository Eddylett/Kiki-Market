from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, ProtectedError, Sum
from django.shortcuts import get_object_or_404, redirect, render

from usuarios.models import Rol
from usuarios.permisos import rol_requerido

from .forms import MermaForm, ProductoForm, RecepcionForm
from .models import Lote, Merma, Producto
GESTION = (Rol.ADMINISTRADOR, Rol.ENCARGADO_INVENTARIO)


@login_required
def producto_lista(request):
    productos = Producto.objects.select_related("categoria", "proveedor").order_by("nombre")
    return render(request, "inventario/producto_lista.html", {"productos": productos})


@rol_requerido(*GESTION)
def producto_crear(request):
    form = ProductoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Producto creado.")
        return redirect("producto_lista")
    return render(request, "inventario/producto_form.html", {"form": form, "titulo": "Nuevo producto"})


@rol_requerido(*GESTION)
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    form = ProductoForm(request.POST or None, instance=producto)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Producto actualizado.")
        return redirect("producto_lista")
    return render(request, "inventario/producto_form.html", {"form": form, "titulo": "Editar producto"})


@rol_requerido(*GESTION)
def producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        try:
            producto.delete()
            messages.success(request, "Producto eliminado.")
        except ProtectedError:
            messages.error(request, "No se puede eliminar: el producto tiene ventas, compras o mermas asociadas.")
        return redirect("producto_lista")
    return render(request, "inventario/producto_eliminar.html", {"producto": producto}) 


@rol_requerido(*GESTION)
def recepcion_crear(request):
    form = RecepcionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            lote = form.save()
            campo = "stock_estanteria" if form.cleaned_data["destino"] == "estanteria" else "stock_bodega"
            Producto.objects.filter(pk=lote.producto_id).update(**{campo: F(campo) + lote.cantidad})
        messages.success(request, "Recepción registrada: el stock fue actualizado.")
        return redirect("lote_lista")
    return render(request, "inventario/recepcion_form.html", {"form": form})


@login_required
def lote_lista(request):
    lotes = Lote.objects.select_related("producto__categoria").order_by("fecha_vencimiento")
    return render(request, "inventario/lote_lista.html", {"lotes": lotes})


@rol_requerido(Rol.ADMINISTRADOR)
def merma_reporte(request):
    mermas = Merma.objects.select_related("lote__producto").order_by("-fecha")
    total = mermas.aggregate(total=Sum("costo_total"))["total"] or 0
    return render(request, "inventario/merma_reporte.html", {"mermas": mermas, "total": total})


@rol_requerido(*GESTION)
def merma_crear(request):
    form = MermaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            merma = form.save(commit=False)
            lote = merma.lote
            merma.costo_total = merma.cantidad * lote.producto.precio_costo
            merma.save()
            Lote.objects.filter(pk=lote.pk).update(cantidad=F("cantidad") - merma.cantidad)
            campo = "stock_estanteria" if form.cleaned_data["origen"] == "estanteria" else "stock_bodega"
            Producto.objects.filter(pk=lote.producto_id).update(**{campo: F(campo) - merma.cantidad})
        messages.success(request, "Merma registrada: el stock fue actualizado.")
        destino = "merma_reporte" if request.user.rol == Rol.ADMINISTRADOR else "lote_lista"
        return redirect(destino)
    return render(request, "inventario/merma_form.html", {"form": form})