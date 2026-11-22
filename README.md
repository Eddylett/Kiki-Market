# Kiki Market
## Evaluación 4 · Ingeniería de Software
## Integrantes: Edgardo Rosales (completar con los demás integrantes del equipo)

Sistema web para un minimarket familiar: productos, lotes con semáforo de vencimiento,
recepción de mercadería, mermas, punto de venta, devoluciones y reportes de gestión.

## IMPORTANTE !
   ```bash
   Esta versión usa una BDD PostgreSQL en Supabase (requiere internet)
   y un archivo .env propio que NO se sube a GitHub.
   ```

## Setup

1. Crear el archivo `.env` en la carpeta principal (junto a `manage.py`):
   ```bash
   SECRET_KEY=(clave del proyecto)
   DEBUG=true
   DATABASE_URL=(cadena de conexión de Supabase)
   ```
2. Crear y activar ambiente (solo la primera vez se crea):
   ```bash
   python -m venv venv
   ```
   Windows (PowerShell):
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   Windows (CMD):
   ```bash
   venv\Scripts\activate
   ```
3. Instalar dependencias (solo la primera vez, o si aparece ModuleNotFoundError):
   ```bash
   pip install -r requirements.txt
   ```
4. Aplicar migraciones de BDD (si dice "No migrations to apply", está todo al día):
   ```bash
   python manage.py migrate
   ```
5. (opcional) crear superusuario (pide usuario, nombre y contraseña; queda con rol Administrador):
   ```bash
   python manage.py createsuperuser
   ```
6. Correr el servidor:
   ```bash
   python manage.py runserver
   ```
7. Visitar http://127.0.0.1:8000/

8. Salir del servidor: `Ctrl + C`

9. Usuarios de prueba (todos tienen la contraseña `Prueba1234*`):
   ```bash
   1. Admin_test  - Administrador: todo, incluye Reportes, Mermas y panel /admin/
   2. bodega1     - Encargado de inventario: productos, lotes, recepción y registrar mermas
   3. cajera1     - Cajera: punto de venta, comprobantes y devoluciones
   ```

## Módulos

| Módulo | Ruta | Roles |
|--------|------|-------|
| Productos | /productos/ | Todos ven; administrador y encargado editan |
| Categorías | /categorias/ | Administrador y encargado de inventario |
| Configuración de alertas de vencimiento | /vencimientos/configuracion/ | Solo administrador |
| Lotes y semáforo | /lotes/ | Todos |
| Recepción de mercadería | /recepcion/ | Administrador, encargado |
| Mermas (reporte) | /mermas/ | Administrador |
| Registrar merma | /mermas/nueva/ | Administrador, encargado |
| Punto de venta | /pos/ | Cajera, administrador |
| Devoluciones | /devolucion/<id>/ | Cajera, administrador |
| Reportes de cierre | /reportes/ | Administrador |

## Categorías y códigos de barras

- Desde **Categorías** se pueden crear, editar y eliminar categorías personalizadas (por ejemplo: Bebidas, Lácteos, Aseo o Congelados).
- Una categoría no se puede eliminar mientras tenga productos asociados. Primero se debe cambiar la categoría de esos productos.
- La clasificación **Perecible / De despensa** se mantiene separada del nombre de la categoría porque sirve para configurar las alertas de vencimiento.
- Al guardar un producto sin código, Kiki Market genera automáticamente un código interno numérico único de 13 dígitos. El código aparece en la lista de productos y se puede utilizar en el punto de venta.

## Pruebas del prototipo

Pruebas manuales con los tres roles, sobre la BDD de Supabase.

| ID | Módulo | Caso | Resultado esperado | Resultado obtenido | Estado |
|----|--------|------|--------------------|--------------------|--------|
| P-01 | Acceso | Iniciar sesión con credenciales válidas | Entra al inicio | (rellenar) | |
| P-02 | Acceso | Contraseña incorrecta | Mensaje de error, no entra | (rellenar) | |
| P-03 | Roles | Cajera abre /reportes/ o /mermas/ | "No tienes permiso para realizar esta acción" | (rellenar) | |

## Alertas automáticas de vencimiento

- Valores predeterminados para perecibles: avisos progresivos a 15, 7 y 3 días.
- Valor predeterminado para despensa: aviso preventivo a 30 días.
- El administrador puede ajustar los umbrales en **Alertas** (`/vencimientos/configuracion/`).
- Las categorías solo definen si sus productos son perecibles o de despensa; el encargado de inventario ya no puede cambiar los días de alerta.
- Los lotes se evalúan usando su fecha de vencimiento y la fecha actual. El semáforo y los avisos se actualizan al consultar o recargar **Lotes y vencimientos**.
- Esta versión no envía correos ni notificaciones push y no ejecuta un proceso de alertas en segundo plano.
- Para crear la nueva tabla de configuración, ejecuta `python manage.py migrate` después de copiar el proyecto actualizado.
