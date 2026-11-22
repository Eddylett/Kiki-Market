from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from usuarios.models import Rol, Usuario

from .forms import ConfiguracionVencimientoForm
from .models import Categoria, ConfiguracionVencimiento, Lote, Producto, TipoProducto


class AlertasVencimientoTests(TestCase):
    def setUp(self):
        self.configuracion = ConfiguracionVencimiento.obtener()
        self.categoria_perecible = Categoria.objects.create(
            nombre="Lácteos", tipo=TipoProducto.PERECIBLE
        )
        self.categoria_despensa = Categoria.objects.create(
            nombre="Abarrotes", tipo=TipoProducto.DESPENSA
        )

    def crear_lote(self, categoria, dias):
        producto = Producto.objects.create(
            categoria=categoria,
            nombre=f"Producto {categoria.nombre} {dias}",
            precio_costo="100",
            precio_venta="150",
            codigo_barra=f"TEST{categoria.pk}{dias}",
        )
        return Lote.objects.create(
            producto=producto,
            numero_lote=f"L-{categoria.pk}-{dias}",
            fecha_vencimiento=timezone.localdate() + timedelta(days=dias),
            cantidad=5,
        )

    def test_perecibles_usan_umbrales_15_7_y_3(self):
        lote_15 = self.crear_lote(self.categoria_perecible, 15)
        lote_7 = self.crear_lote(self.categoria_perecible, 7)
        lote_3 = self.crear_lote(self.categoria_perecible, 3)

        self.assertEqual(lote_15.estado_semaforo(self.configuracion), "amarillo")
        self.assertIn("Aviso preventivo", lote_15.mensaje_alerta(self.configuracion))
        self.assertIn("Prioridad alta", lote_7.mensaje_alerta(self.configuracion))
        self.assertEqual(lote_3.estado_semaforo(self.configuracion), "rojo")
        self.assertIn("urgente", lote_3.mensaje_alerta(self.configuracion).lower())

    def test_despensa_usa_umbral_predeterminado_de_30_dias(self):
        lote_31 = self.crear_lote(self.categoria_despensa, 31)
        lote_30 = self.crear_lote(self.categoria_despensa, 30)
        self.assertEqual(lote_31.estado_semaforo(self.configuracion), "verde")
        self.assertEqual(lote_30.estado_semaforo(self.configuracion), "amarillo")
        self.assertIn("30 días", lote_30.mensaje_alerta(self.configuracion))

    def test_pantalla_de_lotes_muestra_alertas_calculadas(self):
        encargado = Usuario.objects.create_user(
            usuario="encargado_lotes",
            password="Prueba1234*",
            nombre="Encargado",
            rol=Rol.ENCARGADO_INVENTARIO,
        )
        self.crear_lote(self.categoria_perecible, 15)
        self.client.force_login(encargado)
        respuesta = self.client.get("/lotes/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Alertas automáticas")
        self.assertContains(respuesta, "Aviso preventivo")

    def test_formulario_rechaza_umbrales_fuera_de_orden(self):
        form = ConfiguracionVencimientoForm(
            data={
                "perecible_aviso_1": 7,
                "perecible_aviso_2": 15,
                "perecible_aviso_3": 3,
                "despensa_aviso": 30,
            },
            instance=self.configuracion,
        )
        self.assertFalse(form.is_valid())


class AccesoConfiguracionVencimientoTests(TestCase):
    def crear_usuario(self, usuario, rol):
        return Usuario.objects.create_user(
            usuario=usuario,
            password="Prueba1234*",
            nombre=usuario.title(),
            rol=rol,
        )

    def test_solo_administrador_puede_abrir_configuracion(self):
        administrador = self.crear_usuario("admin_alertas", Rol.ADMINISTRADOR)
        self.client.force_login(administrador)
        respuesta_admin = self.client.get("/vencimientos/configuracion/")
        self.assertEqual(respuesta_admin.status_code, 200)
        respuesta_guardado = self.client.post(
            "/vencimientos/configuracion/",
            {
                "perecible_aviso_1": 20,
                "perecible_aviso_2": 10,
                "perecible_aviso_3": 5,
                "despensa_aviso": 40,
            },
        )
        self.assertEqual(respuesta_guardado.status_code, 302)
        configuracion = ConfiguracionVencimiento.obtener()
        self.assertEqual(configuracion.perecible_aviso_1, 20)
        self.assertEqual(configuracion.despensa_aviso, 40)

        self.client.logout()
        encargado = self.crear_usuario("encargado_alertas", Rol.ENCARGADO_INVENTARIO)
        self.client.force_login(encargado)
        respuesta_encargado = self.client.get("/vencimientos/configuracion/")
        self.assertEqual(respuesta_encargado.status_code, 403)
