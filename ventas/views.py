import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import DecimalField, F, Sum
from django.shortcuts import get_object_or_404, redirect, render

from inventario.models import Merma, Producto
from usuarios.models import Rol
from usuarios.permisos import rol_requerido

from .models import DetalleVenta, Devolucion,  MetodoPago, Venta

CAJA = (Rol.CAJERA, Rol.ADMINISTRADOR)

def _entero_positivo(valor, defecto=1):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return defecto
    return numero if numero > 0 else defecto
    
def _carrito(request):
    return request.session.setdefault("carrito", {})


def _agregar(request, producto, cantidad=1):
    carrito = _carrito(request)
    clave = str(producto.pk)
    nueva = carrito.get(clave, 0) + cantidad
    if nueva > producto.stock_total():
        messages.error(request, f"Stock insuficiente de {producto.nombre} (disponible: {producto.stock_total()}).")
        return
    carrito[clave] = nueva
    request.session.modified = True


def _lineas(request):
    carrito = _carrito(request)
    productos = Producto.objects.in_bulk([int(k) for k in carrito])
    lineas, total = [], Decimal("0")
    for clave, cantidad in carrito.items():
        p = productos.get(int(clave))
        if p is None:
            continue
        precio = p.precio_final()
        subtotal = precio * cantidad
        lineas.append({"producto": p, "cantidad": cantidad, "precio": precio, "subtotal": subtotal})
        total += subtotal
    return lineas, total


def _por_codigo(texto):
    if not texto.isdigit():
        return None
    candidatos = {texto, texto.lstrip("0"), texto.zfill(12), texto.zfill(13)}
    return Producto.objects.filter(codigo_barra__in=candidatos).first()


@rol_requerido(*CAJA)
def pos(request):
    q = request.GET.get("q", "").strip()
    cant = _entero_positivo(request.GET.get("cant"))
    resultados = []
    if q:
        exacto = _por_codigo(q)
        if exacto:
            _agregar(request, exacto, cant)
            return redirect("pos")
        resultados = Producto.objects.filter(nombre__icontains=q).order_by("nombre")[:20]
    lineas, total = _lineas(request)
    return render(request, "ventas/pos.html", {
        "q": q,
        "cant": cant,
        "resultados": resultados,
        "lineas": lineas,
        "total": total,
        "metodos": MetodoPago.choices,
    })


@rol_requerido(*CAJA)
def pos_agregar(request):
    if request.method == "POST":
        producto = get_object_or_404(Producto, pk=request.POST.get("producto"))
        _agregar(request, producto, _entero_positivo(request.POST.get("cantidad")))
    return redirect("pos")


@rol_requerido(*CAJA)
def pos_actualizar(request, pk):
    if request.method == "POST":
        producto = get_object_or_404(Producto, pk=pk)
        try:
            cantidad = int(request.POST.get("cantidad", ""))
        except ValueError:
            messages.error(request, "Cantidad no válida.")
            return redirect("pos")
        carrito = _carrito(request)
        if cantidad <= 0:
            carrito.pop(str(pk), None)
        elif cantidad > producto.stock_total():
            messages.error(request, f"Stock insuficiente de {producto.nombre} (disponible: {producto.stock_total()}).")
        else:
            carrito[str(pk)] = cantidad
        request.session.modified = True
    return redirect("pos")


@rol_requerido(*CAJA)
def pos_quitar(request, pk):
    if request.method == "POST":
        _carrito(request).pop(str(pk), None)
        request.session.modified = True
    return redirect("pos")


@rol_requerido(*CAJA)
def pos_confirmar(request):
    if request.method != "POST":
        return redirect("pos")
    lineas, total = _lineas(request)
    if not lineas:
        messages.error(request, "El carro está vacío.")
        return redirect("pos")
    metodo = request.POST.get("metodo_pago")
    if metodo not in MetodoPago.values:
        metodo = MetodoPago.EFECTIVO
    try:
        with transaction.atomic():
            venta = Venta.objects.create(
                usuario=request.user,
                nro_comprobante=f"TMP-{uuid.uuid4().hex[:20]}",
                total_venta=total,
                metodo_pago=metodo,
            )
            for linea in lineas:
                p = Producto.objects.select_for_update().get(pk=linea["producto"].pk)
                cantidad = linea["cantidad"]
                if cantidad > p.stock_total():
                    raise ValueError(f"Stock insuficiente de {p.nombre}.")
                de_estanteria = min(cantidad, p.stock_estanteria)
                de_bodega = cantidad - de_estanteria
                Producto.objects.filter(pk=p.pk).update(
                    stock_estanteria=F("stock_estanteria") - de_estanteria,
                    stock_bodega=F("stock_bodega") - de_bodega,
                )
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=p,
                    cantidad=cantidad,
                    precio_unitario=linea["precio"],
                    costo_unitario=p.precio_costo,
                    subtotal=linea["subtotal"],
                )
            venta.nro_comprobante = f"KM-{venta.pk:06d}"
            venta.save(update_fields=["nro_comprobante"])
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("pos")
    request.session["carrito"] = {}
    return redirect("comprobante", pk=venta.pk)


@rol_requerido(*CAJA)
def comprobante(request, pk):
    venta = get_object_or_404(Venta.objects.select_related("usuario"), pk=pk)
    devoluciones = Devolucion.objects.filter(detalle_venta__venta=venta).select_related("detalle_venta__producto")
    return render(request, "ventas/comprobante.html", {
        "venta": venta,
        "detalles": venta.detalles.select_related("producto"),
        "devoluciones": devoluciones,
    })


@rol_requerido(*CAJA)
def devolucion_crear(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    filas = []
    for d in venta.detalles.select_related("producto"):
        devuelto = d.devoluciones.aggregate(total=Sum("cantidad"))["total"] or 0
        filas.append({"detalle": d, "devuelto": devuelto, "disponible": d.cantidad - devuelto})

    if request.method == "POST":
        motivo = request.POST.get("motivo", "").strip()[:100]
        a_devolver = []
        for fila in filas:
            cantidad = _entero_positivo(request.POST.get(f"cant_{fila['detalle'].pk}"), 0)
            if cantidad > fila["disponible"]:
                messages.error(
                    request,
                    f"De {fila['detalle'].producto.nombre} solo se pueden devolver {fila['disponible']} unidades.",
                )
                return redirect("devolucion_crear", pk=venta.pk)
            if cantidad > 0:
                a_devolver.append((fila["detalle"], cantidad))

        if not a_devolver:
            messages.error(request, "Indica al menos una unidad a devolver.")
        elif not motivo:
            messages.error(request, "Escribe el motivo de la devolución.")
        else:
            with transaction.atomic():
                for detalle, cantidad in a_devolver:
                    Devolucion.objects.create(
                        detalle_venta=detalle,
                        cantidad=cantidad,
                        motivo=motivo,
                        monto=detalle.precio_unitario * cantidad,
                    )
                    Producto.objects.filter(pk=detalle.producto_id).update(
                        stock_estanteria=F("stock_estanteria") + cantidad
                    )
            messages.success(request, "Devolución registrada: el producto volvió al stock.")
            return redirect("comprobante", pk=venta.pk)
        return redirect("devolucion_crear", pk=venta.pk)

    return render(request, "ventas/devolucion_form.html", {"venta": venta, "filas": filas})


ETIQUETAS_PERIODO = {"dia": "Diario", "semana": "Semanal", "mes": "Mensual"}


def _rango(periodo):
    hoy = timezone.localdate()
    if periodo == "dia":
        ini = fin = hoy
        ini_a = fin_a = hoy - timedelta(days=1)
    elif periodo == "semana":
        ini, fin = hoy - timedelta(days=hoy.weekday()), hoy
        ini_a, fin_a = ini - timedelta(days=7), fin - timedelta(days=7)
    else:
        ini, fin = hoy.replace(day=1), hoy
        ultimo_mes_anterior = ini - timedelta(days=1)
        ini_a = ultimo_mes_anterior.replace(day=1)
        fin_a = ultimo_mes_anterior.replace(day=min(hoy.day, ultimo_mes_anterior.day))
    return ini, fin, ini_a, fin_a


def _resumen(ini, fin):
    ventas = Venta.objects.filter(fecha_hora__date__range=(ini, fin))
    detalles = DetalleVenta.objects.filter(venta__in=ventas)
    devoluciones = Devolucion.objects.filter(fecha_hora__date__range=(ini, fin))
    costo_expr = Sum(F("cantidad") * F("costo_unitario"), output_field=DecimalField())

    bruto = ventas.aggregate(t=Sum("total_venta"))["t"] or 0
    costo = detalles.aggregate(t=costo_expr)["t"] or 0
    devuelto = devoluciones.aggregate(t=Sum("monto"))["t"] or 0
    costo_devuelto = devoluciones.aggregate(
        t=Sum(F("cantidad") * F("detalle_venta__costo_unitario"), output_field=DecimalField())
    )["t"] or 0

    neto = bruto - devuelto
    ganancia = neto - (costo - costo_devuelto)

    top = (
        detalles.values("producto__nombre")
        .annotate(unidades=Sum("cantidad"), total=Sum("subtotal"))
        .order_by("-unidades")[:5]
    )

    categorias = []
    filas = (
        detalles.values("producto__categoria__nombre")
        .annotate(ingreso=Sum("subtotal"), costo=costo_expr)
        .order_by("producto__categoria__nombre")
    )
    for f in filas:
        margen = f["ingreso"] - f["costo"]
        porcentaje = round(margen / f["ingreso"] * 100) if f["ingreso"] else 0
        categorias.append({
            "nombre": f["producto__categoria__nombre"],
            "ingreso": f["ingreso"],
            "margen": margen,
            "porcentaje": porcentaje,
        })

    mermas = Merma.objects.filter(fecha__range=(ini, fin)).aggregate(t=Sum("costo_total"))["t"] or 0

    return {
        "num_ventas": ventas.count(),
        "neto": neto,
        "devuelto": devuelto,
        "ganancia": ganancia,
        "top": top,
        "categorias": categorias,
        "mermas": mermas,
    }


def _variacion(actual, anterior):
    if not anterior:
        return None
    return round((actual - anterior) / anterior * 100)


@rol_requerido(Rol.ADMINISTRADOR)
def reporte_cierre(request):
    periodo = request.GET.get("periodo", "dia")
    if periodo not in ETIQUETAS_PERIODO:
        periodo = "dia"
    ini, fin, ini_a, fin_a = _rango(periodo)
    actual = _resumen(ini, fin)
    anterior = _resumen(ini_a, fin_a)
    graficos = {
        "top": {
            "etiquetas": [p["producto__nombre"] for p in actual["top"]],
            "unidades": [p["unidades"] for p in actual["top"]],
            "vendido": [float(p["total"]) for p in actual["top"]],
        },
        "categorias": {
            "etiquetas": [c["nombre"] for c in actual["categorias"]],
            "vendido": [float(c["ingreso"]) for c in actual["categorias"]],
            "margen": [float(c["margen"]) for c in actual["categorias"]],
            "porcentaje": [c["porcentaje"] for c in actual["categorias"]],
        },
        "comparacion": {
            "actual": [float(actual["neto"]), float(actual["ganancia"])],
            "anterior": [float(anterior["neto"]), float(anterior["ganancia"])],
        },
    }
    return render(request, "ventas/reporte_cierre.html", {
        "periodo": periodo,
        "ini": ini, "fin": fin, "ini_a": ini_a, "fin_a": fin_a,
        "r": actual,
        "graficos": graficos,
        "var_ventas": _variacion(actual["neto"], anterior["neto"]),
        "var_ganancia": _variacion(actual["ganancia"], anterior["ganancia"]),
    })



def _periodo_y_fechas(request):
    periodo = request.GET.get("periodo", "dia")
    if periodo not in ETIQUETAS_PERIODO:
        periodo = "dia"
    ini, fin, _, _ = _rango(periodo)
    return periodo, ini, fin


def _lineas_vendidas(ini, fin):
    return DetalleVenta.objects.filter(venta__fecha_hora__date__range=(ini, fin))


@rol_requerido(Rol.ADMINISTRADOR)
def reporte_ventas(request):
    periodo, ini, fin = _periodo_y_fechas(request)
    ventas = (
        Venta.objects.filter(fecha_hora__date__range=(ini, fin))
        .select_related("usuario")
        .order_by("-fecha_hora")
    )
    devoluciones = (
        Devolucion.objects.filter(fecha_hora__date__range=(ini, fin))
        .select_related("detalle_venta__venta", "detalle_venta__producto")
        .order_by("-fecha_hora")
    )
    return render(request, "ventas/reporte_ventas.html", {
        "periodo": periodo, "ini": ini, "fin": fin,
        "ventas": ventas, "devoluciones": devoluciones,
    })


@rol_requerido(Rol.ADMINISTRADOR)
def reporte_productos(request):
    periodo, ini, fin = _periodo_y_fechas(request)
    filas = (
        _lineas_vendidas(ini, fin)
        .values("producto__nombre", "producto__categoria__nombre")
        .annotate(
            unidades=Sum("cantidad"),
            vendido=Sum("subtotal"),
            costo=Sum(F("cantidad") * F("costo_unitario"), output_field=DecimalField()),
        )
        .order_by("-unidades")
    )
    productos = [
        {
            "nombre": f["producto__nombre"],
            "categoria": f["producto__categoria__nombre"],
            "unidades": f["unidades"],
            "vendido": f["vendido"],
            "margen": f["vendido"] - f["costo"],
        }
        for f in filas
    ]
    return render(request, "ventas/reporte_productos.html", {
        "periodo": periodo, "ini": ini, "fin": fin, "productos": productos,
    })


@rol_requerido(Rol.ADMINISTRADOR)
def reporte_categorias(request):
    periodo, ini, fin = _periodo_y_fechas(request)
    filas = (
        _lineas_vendidas(ini, fin)
        .values("producto__categoria__nombre", "producto__nombre")
        .annotate(
            unidades=Sum("cantidad"),
            vendido=Sum("subtotal"),
            costo=Sum(F("cantidad") * F("costo_unitario"), output_field=DecimalField()),
        )
        .order_by("producto__categoria__nombre", "-vendido")
    )
    agrupadas = {}
    for f in filas:
        nombre = f["producto__categoria__nombre"]
        cat = agrupadas.setdefault(
            nombre, {"nombre": nombre, "vendido": 0, "costo": 0, "productos": []}
        )
        cat["vendido"] += f["vendido"]
        cat["costo"] += f["costo"]
        cat["productos"].append({
            "nombre": f["producto__nombre"],
            "unidades": f["unidades"],
            "vendido": f["vendido"],
            "margen": f["vendido"] - f["costo"],
        })
    categorias = []
    for cat in agrupadas.values():
        cat["margen"] = cat["vendido"] - cat["costo"]
        cat["porcentaje"] = round(cat["margen"] / cat["vendido"] * 100) if cat["vendido"] else 0
        categorias.append(cat)
    return render(request, "ventas/reporte_categorias.html", {
        "periodo": periodo, "ini": ini, "fin": fin, "categorias": categorias,
    })