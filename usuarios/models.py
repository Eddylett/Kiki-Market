from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class Rol(models.TextChoices):
    ADMINISTRADOR = "administrador", "Administrador"
    ENCARGADO_INVENTARIO = "encargado_inventario", "Encargado de inventario"
    CAJERA = "cajera", "Cajera"


class UsuarioManager(BaseUserManager):
    def _crear(self, usuario, password, **extra):
        if not usuario:
            raise ValueError("El nombre de usuario es obligatorio")
        obj = self.model(usuario=usuario, **extra)
        obj.set_password(password)
        obj.save(using=self._db)
        return obj

    def create_user(self, usuario, password=None, **extra):
        extra.setdefault("rol", Rol.CAJERA)
        return self._crear(usuario, password, **extra)

    def create_superuser(self, usuario, password=None, **extra):
        extra["rol"] = Rol.ADMINISTRADOR  # el dueño
        return self._crear(usuario, password, **extra)


class Usuario(AbstractBaseUser):
    """Tabla `usuarios`: id_usuario, nombre, usuario, contraseñahash, rol."""

    id_usuario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    usuario = models.CharField(max_length=50, unique=True)
    password = models.CharField("contraseña (hash)", max_length=255, db_column="contraseñahash")
    rol = models.CharField(max_length=30, choices=Rol.choices)

    last_login = None  # la tabla del informe no tiene este campo

    USERNAME_FIELD = "usuario"
    REQUIRED_FIELDS = ["nombre"]
    objects = UsuarioManager()

    class Meta:
        db_table = "usuarios"

    def __str__(self):
        return f"{self.nombre} ({self.get_rol_display()})"