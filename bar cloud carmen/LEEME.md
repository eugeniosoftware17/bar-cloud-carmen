# Bar Cloud — Carmen

Sistema Django para el negocio de bebidas de Carmen.

## Estructura
- `config/` → configuración del proyecto (settings, urls)
- `apps/` → un módulo por carpeta (productos, mesas, ventas, inventario…)
- `templates/` → plantillas HTML (diseño Nuevo)
- `static/` → CSS, JS e imágenes
- `media/` → archivos subidos (fotos de productos)
- `.env` → claves y configuración local (no se sube a git; ver `.env.example`)

## Diseño
Plantillas basadas en `02-DISEÑO/Nuevo` (Bar Cloud, blanco y negro, modo claro/oscuro).
- `templates/base.html` → menú lateral, menú del usuario y barra de celular
- `static/css/estilos.css` → copia de los estilos del diseño Nuevo
- `static/css/login.css` y `templates/usuarios/login.html` → pantalla de entrada

## Login y permisos
- Entrada: http://127.0.0.1:8000/entrar/ (todas las pantallas piden sesión). Al entrar, cada usuario
  va al primer módulo que tiene permitido.
- El **dueño** (superusuario) tiene todo.
- A los demás, en **Usuarios** se les marca cada módulo: *Sin acceso*, *Solo ver* o *Ver y editar*
  (con atajos "Caja", "Todo" y "Quitar todo"). Reglas en `apps/usuarios/permisos.py`;
  qué permite "editar" en cada módulo está en `apps/usuarios/models.py` (`MODULOS`).
- Nadie cambia sus propios permisos ni se desactiva; solo el dueño toca la cuenta del dueño.

## Módulos hechos
- **Productos** (`apps/productos`): categorías (Bebidas, Comida, Snacks, Otros), precio, costo, margen,
  stock inicial, aviso de poco stock, dibujo o foto, activar/desactivar. El cajero solo consulta.
  El stock de un producto ya creado se cambiará desde Inventario.
- **Venta directa**: productos activos por categoría, búsqueda, cuenta, pre-cuenta impresa y **Cobrar**
  (efectivo con cambio, tarjeta o transferencia con referencia).
- **Ventas** (`apps/ventas`): al cobrar se guarda la venta y se descuenta el stock; el servidor recalcula
  precios y totales (propina 10 % e ITBIS 18 %, en `settings.py`). Recibo de 80 mm en `/ventas/<n>/recibo/`.
  Historial con resumen y filtros, detalle y **anular** con motivo (devuelve el stock). Solo el administrador
  ve el historial y anula. Las reglas están en `apps/ventas/servicios.py`.
- **Inventario** (`apps/inventario`, solo administrador): existencias con valor a costo, entradas de mercancía
  (actualizan el costo), ajustes por conteo con motivo, historial de movimientos y lista para pedir (imprimible).
  Todo cambio de stock pasa por `apps/inventario/servicios.py` y deja su movimiento: ventas, anulaciones,
  entradas, ajustes y el stock inicial de productos nuevos. El menú muestra cuántos productos tienen poco stock.
- **Cierre del día** (pestaña en Ventas, `apps/ventas/cierre.py`): resumen del día, por método de pago,
  más vendidos, cuadre de caja (fondo + ventas en efectivo vs. efectivo contado), nota, hoja impresa de 80 mm
  y lista de cierres anteriores. Se puede actualizar; avisa si hubo ventas después de cerrar.
- **Configuración** (`apps/configuracion`, solo administrador): nombre que sale en la factura, dirección,
  teléfono; cobrar o no la propina legal y el ITBIS (y sus porcentajes); recibo en dos copias (COPIA CLIENTE y
  COPIA NEGOCIO en la misma impresión, viene activado; `?copias=1` reimprime solo la del cliente); textos del recibo (quién atendió,
  mensaje de despedida y aviso "sin valor fiscal"). Tiene vista previa del recibo.
  `NEGOCIO_NOMBRE` y `NEGOCIO_DIRECCION` del `.env` solo se usan la primera vez.
- **Usuarios**: crear usuarios, darles permisos por módulo (ver / ver y editar), desactivar y cambiar contraseñas.
- **Proveedores** (`apps/proveedores`): nombre, contacto, teléfono, qué suple y nota; buscador; compras
  registradas y última entrada (salen de las entradas de Inventario). Al registrar una entrada se elige el
  proveedor. Si se elimina un proveedor, sus entradas se conservan sin proveedor.
- **Reportes** (`apps/reportes`, cálculos en `calculos.py`):
  - *Estadísticas*: ventas netas, cantidad, ticket promedio y ganancia bruta (hoy, 7 o 30 días); ventas por
    día/semana/mes; productos más y menos vendidos; horas de más movimiento; totales por método de pago.
  - *Gastos y ganancias*: registrar gastos por categoría y ver, por mes, ventas netas − costo de lo vendido −
    gastos = ganancia neta. La propina y el ITBIS no cuentan como ingreso.
- **Mesas** (`apps/mesas`): 8 mesas iniciales, abrir cuenta, agregar o quitar consumos (aparta el stock entre
  mesas), pre-cuenta impresa, cobrar (misma ventana de cobro que Venta directa, `static/js/caja.js`) y liberar.
  El stock se descuenta al cobrar. La pantalla se actualiza sola cada 30 s para ver lo que hacen otras cajas.
  Al abrir una mesa se elige **quién la atiende** (mesera): se toca un nombre de la lista o se escribe uno nuevo,
  que queda guardado. Se puede cambiar con la cuenta abierta y quitar nombres de la lista con la ×.
  El nombre sale en la tarjeta de la mesa, la pre-cuenta, el recibo ("Atendió") y el historial de ventas,
  y Reportes muestra ventas, cuentas y propina por mesera.

## Cómo correrlo (PowerShell)
```powershell
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```
Abrir http://127.0.0.1:8000/

## Pruebas
```powershell
python manage.py test apps
```

## Primera vez en otra computadora
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # y poner una SECRET_KEY nueva
python manage.py migrate
python manage.py createsuperuser
```

## Stack
- Python 3.12 · Django 5.2 (LTS)
- SQLite por ahora (cambiar cuando se defina el hosting)
