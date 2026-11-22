from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            if request.user.rol not in roles:
                return HttpResponseForbidden("No tienes permiso para realizar esta acción.")
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador