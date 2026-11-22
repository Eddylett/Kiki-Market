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
   Mac/Linux:
   ```bash
   source venv/bin/activate
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
| Lotes y semáforo | /lotes/ | Todos |
| Recepción de mercadería | /recepcion/ | Administrador, encargado |
| Mermas (reporte) | /mermas/ | Administrador |
| Registrar merma | /mermas/nueva/ | Administrador, encargado |
| Punto de venta | /pos/ | Cajera, administrador |
| Devoluciones | /devolucion/<id>/ | Cajera, administrador |
| Reportes de cierre | /reportes/ | Administrador |

## Pruebas del prototipo

Pruebas manuales con los tres roles, sobre la BDD de Supabase.

| ID | Módulo | Caso | Resultado esperado | Resultado obtenido | Estado |
|----|--------|------|--------------------|--------------------|--------|
| P-01 | Acceso | Iniciar sesión con credenciales válidas | Entra al inicio | (rellenar) | |
| P-02 | Acceso | Contraseña incorrecta | Mensaje de error, no entra | (rellenar) | |
| P-03 | Roles | Cajera abre /reportes/ o /mermas/ | "No tienes permiso para realizar esta acción" | (rellenar) | |