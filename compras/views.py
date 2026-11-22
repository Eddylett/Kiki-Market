from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.core.mail import send_mail
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.shortcuts import redirect, render

from inventario.models import Producto
from usuarios.models import Rol
from usuarios.permisos import rol_requerido

from .models import AlertaStock, DetalleCompra, EstadoOrden, OrdenCompra


def _criticos():
    return (
        Producto.objects.select_related("proveedor")
        .annotate(total=F("stock_estanteria") + F("stock_bodega"))
        .filter(total__lte=F("stock_minimo"))
        .order_by("total", "nombre")
    )


def _sugerida(producto):
    return max(producto.stock_minimo * 2 - producto.stock_total(), 1)


def _con_orden_pendiente():
    return set(
        DetalleCompra.objects.filter(orden__estado=EstadoOrden.PENDIENTE)
        .values_list("producto_id", flat=True)
    )


@rol_requerido(Rol.ADMINISTRADOR)
def reposicion(request):
    pendientes = _con_orden_pendiente()

    if request.method == "POST":
        ids = request.POST.getlist("producto")
        elegidos = [
            p for p in _criticos()
            if str(p.pk) in ids and p.proveedor_id and p.pk not in pendientes
        ]
        if not elegidos:
            messages.error(request, "Elige al menos un producto con proveedor y sin orden pendiente.")
            return redirect("orden_lista")

        por_proveedor = {}
        for p in elegidos:
            por_proveedor.setdefault(p.proveedor, []).append(p)

        with transaction.atomic():
            for proveedor, productos in por_proveedor.items():
                alertas = [
                    AlertaStock.objects.create(producto=p, stock=p.stock_total(), atendida=True)
                    for p in productos
                ]
                orden = OrdenCompra.objects.create(proveedor=proveedor, alerta=alertas[0])
                total = 0
                for p in productos:
                    cantidad = _sugerida(p)
                    subtotal = cantidad * p.precio_costo
                    DetalleCompra.objects.create(
                        orden=orden, producto=p, cantidad_sugerida=cantidad,
                        costo_unitario=p.precio_costo, subtotal=subtotal,
                    )
                    total += subtotal
                orden.total_estimado = total
                orden.save(update_fields=["total_estimado"])

        messages.success(
            request,
            f"Se generaron {len(por_proveedor)} orden(es) de compra pendientes de aprobación. "
            "No se envió nada al proveedor.",
        )
        return redirect("reposicion")

    filas = [
        {"producto": p, "sugerida": _sugerida(p), "pendiente": p.pk in pendientes}
        for p in _criticos()
    ]
    return render(request, "compras/reposicion.html", {"filas": filas})

@rol_requerido(Rol.ADMINISTRADOR)
def orden_lista(request):
    ordenes = OrdenCompra.objects.select_related("proveedor").order_by("-fecha_creacion")
    return render(request, "compras/orden_lista.html", {"ordenes": ordenes})


def _texto_correo(orden, usuario):
    proveedor = orden.proveedor
    lineas = [
        f"Hola {proveedor.contacto_nombre or proveedor.razon_social},",
        "",
        f"Kiki Market solicita la siguiente reposición (orden #{orden.pk}):",
        "",
    ]
    for d in orden.detalles.select_related("producto").filter(cantidad_aprobada__gt=0):
        lineas.append(f"- {d.producto.nombre}: {d.cantidad_aprobada} unidades")
    lineas += [
        "",
        f"Total estimado: ${int(orden.total_estimado)}",
        f"Aprobada por: {usuario.nombre}",
        "",
        "Gracias,",
        "Kiki Market",
    ]
    return "\n".join(lineas)


@rol_requerido(Rol.ADMINISTRADOR)
def orden_detalle(request, pk):
    orden = get_object_or_404(OrdenCompra.objects.select_related("proveedor", "usuario"), pk=pk)
    detalles = list(orden.detalles.select_related("producto"))
    editable = orden.estado == EstadoOrden.PENDIENTE

    if request.method == "POST" and editable:
        accion = request.POST.get("accion")

        if accion == "rechazar":
            orden.estado = EstadoOrden.RECHAZADA
            orden.save(update_fields=["estado"])
            messages.success(request, "Orden rechazada. No se envió nada al proveedor.")
            return redirect("orden_lista")

        if accion == "aprobar":
            try:
                cantidades = {d.pk: int(request.POST.get(f"cant_{d.pk}", "")) for d in detalles}
            except ValueError:
                messages.error(request, "Revisa las cantidades: deben ser números enteros.")
                return redirect("orden_detalle", pk=orden.pk)
            if any(c < 0 for c in cantidades.values()) or sum(cantidades.values()) == 0:
                messages.error(request, "Las cantidades no pueden ser negativas y debe haber al menos una unidad.")
                return redirect("orden_detalle", pk=orden.pk)

            with transaction.atomic():
                total = 0
                for d in detalles:
                    d.cantidad_aprobada = cantidades[d.pk]
                    d.subtotal = d.cantidad_aprobada * d.costo_unitario
                    d.save(update_fields=["cantidad_aprobada", "subtotal"])
                    total += d.subtotal
                orden.total_estimado = total
                orden.estado = EstadoOrden.APROBADA
                orden.usuario = request.user
                orden.fecha_aprobacion = timezone.now()
                orden.save()

            try:
                send_mail(
                    f"Orden de compra #{orden.pk} · Kiki Market",
                    _texto_correo(orden, request.user),
                    None,
                    [orden.proveedor.correo],
                )
                orden.estado = EstadoOrden.ENVIADA
                orden.save(update_fields=["estado"])
                messages.success(request, f"Orden aprobada y enviada a {orden.proveedor.correo}.")
            except Exception:
                messages.error(
                    request,
                    "La orden quedó aprobada, pero no se pudo enviar el correo. Revisa la configuración de correo.",
                )
            return redirect("orden_detalle", pk=orden.pk)

    return render(request, "compras/orden_detalle.html", {
        "orden": orden, "detalles": detalles, "editable": editable,
    })