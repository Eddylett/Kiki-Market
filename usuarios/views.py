from django.contrib.auth.decorators import login_required
from django.shortcuts import render


from .models import Rol
from .permisos import rol_requerido

@rol_requerido(Rol.ADMINISTRADOR)
def panel_admin(request):
    return render(request, "usuarios/panel_admin.html")

@login_required
def inicio(request):
    return render(request, "usuarios/inicio.html")