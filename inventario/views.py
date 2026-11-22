from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, F, ProtectedError, Sum
from django.shortcuts import get_object_or_404, redirect, render

from usuarios.models import Rol
from usuarios.permisos import rol_requerido

from .forms import CategoriaForm, ConfiguracionVencimientoForm, MermaForm, ProductoForm, RecepcionForm
from .models import Categoria, ConfiguracionVencimiento, Lote, Merma, Producto
GESTION = (Rol.ADMINISTRADOR, Rol.ENCARGADO_INVENTARIO)


@login_required
def producto_lista(request):
    configuracion = ConfiguracionVencimiento.obtener()
    productos = list(Producto.objects.select_related("categoria", "proveedor").prefetch_related("lotes").order_by("nombre"))
    for producto in productos:
        lotes = [l for l in producto.lotes.all() if l.cantidad > 0]
        lotes.sort(key=lambda l: l.fecha_vencimiento)
        lote = lotes[0] if lotes else None
        producto.estado_vencimiento_actual = producto.estado_vencimiento(configuracion)
        producto.dias_minimos_vencimiento = lote.dias_para_vencer() if lote else None
    return render(request, "inventario/producto_lista.html", {
        "productos": productos,
        "configuracion_vencimiento": configuracion,
    })


@rol_requerido(Rol.ADMINISTRADOR)
def configurar_vencimientos(request):
    configuracion = ConfiguracionVencimiento.obtener()
    form = ConfiguracionVencimientoForm(request.POST or None, instance=configuracion)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Los umbrales de vencimiento fueron actualizados. El semáforo aplicará los nuevos valores automáticamente.")
        return redirect("configurar_vencimientos")
    return render(request, "inventario/configuracion_vencimientos.html", {
        "form": form,
        "configuracion": configuracion,
    })


@rol_requerido(*GESTION)
def categoria_lista(request):
    categorias = Categoria.objects.annotate(
        cantidad_productos=Count("productos")
    ).order_by("nombre")
    return render(request, "inventario/categoria_lista.html", {"categorias": categorias})


@rol_requerido(*GESTION)
def categoria_crear(request):
    form = CategoriaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        categoria = form.save()
        messages.success(request, f'La categoría "{categoria.nombre}" fue creada.')
        return redirect("categoria_lista")
    return render(request, "inventario/categoria_form.html", {
        "form": form,
        "titulo": "Nueva categoría",
    })


@rol_requerido(*GESTION)
def categoria_editar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    form = CategoriaForm(request.POST or None, instance=categoria)
    if request.method == "POST" and form.is_valid():
        categoria = form.save()
        messages.success(request, f'La categoría "{categoria.nombre}" fue actualizada.')
        return redirect("categoria_lista")
    return render(request, "inventario/categoria_form.html", {
        "form": form,
        "titulo": "Editar categoría",
        "categoria": categoria,
    })


@rol_requerido(*GESTION)
def categoria_eliminar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == "POST":
        if categoria.productos.exists():
            messages.error(
                request,
                "No se puede eliminar esta categoría porque tiene productos asociados. "
                "Edita esos productos y asígnales otra categoría primero.",
            )
            return redirect("categoria_lista")
        try:
            nombre = categoria.nombre
            categoria.delete()
            messages.success(request, f'La categoría "{nombre}" fue eliminada.')
        except ProtectedError:
            messages.error(request, "No se puede eliminar la categoría porque está en uso.")
        return redirect("categoria_lista")
    return render(request, "inventario/categoria_eliminar.html", {"categoria": categoria})


@rol_requerido(*GESTION)
def producto_crear(request):
    form = ProductoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        producto = form.save()
        messages.success(
            request,
            f"Producto creado. Código de barras asignado: {producto.codigo_barra}",
        )
        return redirect("producto_lista")
    return render(request, "inventario/producto_form.html", {"form": form, "titulo": "Nuevo producto"})


@rol_requerido(*GESTION)
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    form = ProductoForm(request.POST or None, instance=producto)
    if request.method == "POST" and form.is_valid():
        producto = form.save()
        messages.success(
            request,
            f"Producto actualizado. Código de barras: {producto.codigo_barra}",
        )
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
    configuracion = ConfiguracionVencimiento.obtener()
    lotes = list(
        Lote.objects.select_related("producto__categoria").order_by("fecha_vencimiento")
    )
    alertas_vencimiento = []
    for lote in lotes:
        lote.dias_restantes = lote.dias_para_vencer()
        lote.semaforo_actual = lote.estado_semaforo(configuracion)
        lote.mensaje_alerta_actual = lote.mensaje_alerta(configuracion)
        if lote.cantidad > 0 and lote.mensaje_alerta_actual:
            alertas_vencimiento.append(lote)
    return render(request, "inventario/lote_lista.html", {
        "lotes": lotes,
        "alertas_vencimiento": alertas_vencimiento,
        "configuracion_vencimiento": configuracion,
    })


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