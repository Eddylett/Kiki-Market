from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from inventario.models import ConfiguracionVencimiento, Lote, Producto
from ventas.models import Devolucion, Venta
from ventas.views import _resumen

from .models import Rol

DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


@login_required
def inicio(request):
    usuario = request.user
    hoy = timezone.localdate()
    es_admin = usuario.rol == Rol.ADMINISTRADOR
    es_gestion = usuario.rol in (Rol.ADMINISTRADOR, Rol.ENCARGADO_INVENTARIO)
    contexto = {"es_admin": es_admin, "es_gestion": es_gestion}

    # Avisos del día: stock crítico y lotes en riesgo (administrador y encargado)
    if es_gestion:
        contexto["productos_criticos"] = (
            Producto.objects.annotate(total=F("stock_estanteria") + F("stock_bodega"))
            .filter(total__lte=F("stock_minimo"))
            .count()
        )
        rojos = amarillos = vencidos = 0
        configuracion_vencimiento = ConfiguracionVencimiento.obtener()
        lotes = Lote.objects.select_related("producto__categoria").filter(cantidad__gt=0)
        for lote in lotes:
            estado = lote.estado_semaforo(configuracion_vencimiento)
            if estado == "rojo":
                rojos += 1
                if lote.dias_para_vencer() < 0:
                    vencidos += 1
            elif estado == "amarillo":
                amarillos += 1
        contexto.update(lotes_rojos=rojos, lotes_amarillos=amarillos, lotes_vencidos=vencidos)

    # Resumen de ventas del día con gráficos (solo administrador)
    if es_admin:
        resumen = _resumen(hoy, hoy)
        desde = hoy - timedelta(days=6)
        ventas_por_dia = dict(
            Venta.objects.filter(fecha_hora__date__range=(desde, hoy))
            .annotate(dia=TruncDate("fecha_hora"))
            .values("dia")
            .annotate(t=Sum("total_venta"))
            .values_list("dia", "t")
        )
        devuelto_por_dia = dict(
            Devolucion.objects.filter(fecha_hora__date__range=(desde, hoy))
            .annotate(dia=TruncDate("fecha_hora"))
            .values("dia")
            .annotate(t=Sum("monto"))
            .values_list("dia", "t")
        )
        etiquetas, neto = [], []
        for i in range(7):
            dia = desde + timedelta(days=i)
            etiquetas.append(f"{DIAS_CORTOS[dia.weekday()]} {dia.day}")
            neto.append(float(ventas_por_dia.get(dia, 0) - devuelto_por_dia.get(dia, 0)))
        contexto["resumen_hoy"] = resumen
        contexto["graficos"] = {
            "dias": {"etiquetas": etiquetas, "neto": neto},
            "top": {
                "etiquetas": [p["producto__nombre"] for p in resumen["top"]],
                "unidades": [p["unidades"] for p in resumen["top"]],
                "vendido": [float(p["total"]) for p in resumen["top"]],
            },
        }
    elif usuario.rol == Rol.CAJERA:
        contexto["mis_ventas_hoy"] = Venta.objects.filter(
            usuario=usuario, fecha_hora__date=hoy
        ).count()

    return render(request, "usuarios/inicio.html", contexto)
