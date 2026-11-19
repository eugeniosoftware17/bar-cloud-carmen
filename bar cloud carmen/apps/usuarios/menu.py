"""Menú lateral (diseño Nuevo). Cada usuario ve solo los módulos que tiene permitidos."""

MENU = [
    {
        'clave': 'venta_directa', 'url': 'venta_directa:inicio', 'texto': 'Venta directa',
        'icono': '<circle cx="9" cy="20" r="1"/><circle cx="18" cy="20" r="1"/><path d="M2 3h3l2.7 12.4a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.6L21 7H6"/>',
    },
    {
        'clave': 'mesas', 'url': 'mesas:inicio', 'texto': 'Mesas',
        'icono': '<path d="M3 9h18M5 9v10M19 9v10M8 9V5h8v4M5 14h14"/>',
    },
    {
        'clave': 'productos', 'url': 'productos:inicio', 'texto': 'Productos',
        'icono': '<path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
    },
    {
        'clave': 'inventario', 'url': 'inventario:inicio', 'texto': 'Inventario',
        'icono': '<path d="M3 9l9-6 9 6v11H3z"/><path d="M9 20v-6h6v6"/>',
    },
    {
        'clave': 'ventas', 'url': 'ventas:inicio', 'texto': 'Ventas',
        'icono': '<path d="M3 17l5-5 4 3 8-9"/><path d="M3 21h18"/>',
    },
    {
        'clave': 'proveedores', 'url': 'proveedores:inicio', 'texto': 'Proveedores',
        'icono': '<path d="M2 6h11v10H2zM13 9h4l4 4v3h-8"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
    },
    {
        'clave': 'reportes', 'url': 'reportes:inicio', 'texto': 'Reportes',
        'icono': '<path d="M5 21V10M12 21V4M19 21v-8"/>',
    },
    {
        'clave': 'usuarios', 'url': 'usuarios:inicio', 'texto': 'Usuarios',
        'icono': '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.5 3-6 6.5-6s6.5 2.5 6.5 6"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14c2 .6 3.5 2.6 3.5 6"/>',
    },
    {
        'clave': 'configuracion', 'url': 'configuracion:inicio', 'texto': 'Configuración',
        'icono': '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    },
]
