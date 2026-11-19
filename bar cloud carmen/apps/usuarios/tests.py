import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import CLAVES, Permiso
from .permisos import PLANTILLA_CAJA, guardar_permisos, permisos_de, puede

MODULOS_ADMIN = ['inventario', 'ventas', 'proveedores', 'reportes', 'usuarios', 'configuracion']
MODULOS_CAJA = ['venta_directa', 'mesas', 'productos']


class LoginTests(TestCase):
    def setUp(self):
        self.cajero = User.objects.create_user('caja1', password='prueba-segura-123')
        guardar_permisos(self.cajero, PLANTILLA_CAJA)
        self.duena = User.objects.create_superuser('carmen', password='prueba-segura-123')

    def test_sin_sesion_redirige_al_login(self):
        r = self.client.get(reverse('venta_directa:inicio'))
        self.assertRedirects(r, reverse('login') + '?next=/')

    def test_pagina_login_carga(self):
        self.assertContains(self.client.get(reverse('login')), 'Iniciar sesión')

    def test_login_correcto_entra_a_venta_directa(self):
        r = self.client.post(reverse('login'), {'username': 'caja1', 'password': 'prueba-segura-123'})
        self.assertRedirects(r, reverse('venta_directa:inicio'))

    def test_login_va_al_primer_modulo_permitido(self):
        u = User.objects.create_user('bodega', password='prueba-segura-123')
        guardar_permisos(u, {'inventario': 'editar'})
        r = self.client.post(reverse('login'), {'username': 'bodega', 'password': 'prueba-segura-123'})
        self.assertRedirects(r, reverse('inventario:inicio'))

    def test_login_incorrecto_muestra_error(self):
        r = self.client.post(reverse('login'), {'username': 'caja1', 'password': 'mala'})
        self.assertContains(r, 'Usuario o contraseña incorrectos.')

    def test_cerrar_sesion(self):
        self.client.force_login(self.cajero)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))

    def test_cajero_ve_solo_sus_modulos(self):
        self.client.force_login(self.cajero)
        for m in MODULOS_CAJA:
            self.assertEqual(self.client.get(reverse(f'{m}:inicio')).status_code, 200, m)
        for m in MODULOS_ADMIN:
            self.assertContains(self.client.get(reverse(f'{m}:inicio')), 'No tienes acceso', status_code=403)
        r = self.client.get(reverse('venta_directa:inicio'))
        self.assertNotContains(r, 'Inventario</a>')

    def test_dueno_ve_todo(self):
        self.client.force_login(self.duena)
        for m in MODULOS_CAJA + MODULOS_ADMIN:
            self.assertEqual(self.client.get(reverse(f'{m}:inicio')).status_code, 200, m)

    def test_menu_no_tiene_clientes(self):
        self.client.force_login(self.duena)
        self.assertNotContains(self.client.get(reverse('venta_directa:inicio')), 'Clientes')


class PermisosTests(TestCase):
    """Cada módulo: sin acceso, solo ver o ver y editar."""

    def setUp(self):
        from apps.productos.models import Categoria, Producto
        self.u = User.objects.create_user('ana', password='prueba-segura-123')
        self.p = Producto.objects.create(nombre='Cerveza', categoria=Categoria.objects.get(nombre='Bebidas'), precio=150, stock=10)
        self.client.force_login(self.u)

    def test_dueno_tiene_todo(self):
        d = User.objects.create_superuser('d', password='x')
        self.assertEqual(permisos_de(d), {c: 'editar' for c in CLAVES})

    def test_solo_ver_productos(self):
        guardar_permisos(self.u, {'productos': 'ver'})
        r = self.client.get(reverse('productos:inicio'))
        self.assertContains(r, 'Cerveza')
        self.assertNotContains(r, '+ Nuevo producto')
        self.assertNotContains(r, 'Margen')
        self.assertContains(self.client.get(reverse('productos:nuevo')), 'solo puede ver', status_code=403)

    def test_editar_productos(self):
        guardar_permisos(self.u, {'productos': 'editar'})
        r = self.client.get(reverse('productos:inicio'))
        self.assertContains(r, '+ Nuevo producto')
        self.assertContains(r, 'Margen')
        self.assertEqual(self.client.get(reverse('productos:nuevo')).status_code, 200)

    def test_venta_directa_solo_ver_no_cobra(self):
        guardar_permisos(self.u, {'venta_directa': 'ver'})
        self.assertContains(self.client.get(reverse('venta_directa:inicio')), 'data-solo-ver')
        r = self.client.post(reverse('ventas:cobrar'), json.dumps({'lineas': [{'id': self.p.pk, 'cantidad': 1}], 'metodo': 'Tarjeta'}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()['error'], 'No tienes permiso para hacer esto.')

    def test_mesas_solo_ver(self):
        from apps.mesas.models import Mesa
        guardar_permisos(self.u, {'mesas': 'ver'})
        m = Mesa.objects.first()
        r = self.client.get(reverse('mesas:inicio') + f'?mesa={m.pk}')
        self.assertContains(r, 'solo puede ver las mesas')
        self.assertNotContains(r, '+ Agregar mesa')
        r = self.client.post(reverse('mesas:abrir', args=[m.pk]), '{}', content_type='application/json')
        self.assertEqual(r.status_code, 403)

    def test_inventario_ver_vs_editar(self):
        guardar_permisos(self.u, {'inventario': 'ver'})
        self.assertNotContains(self.client.get(reverse('inventario:inicio')), '+ Registrar entrada')
        self.assertEqual(self.client.post(reverse('inventario:entrada'), {'producto': self.p.pk, 'cantidad': 1}).status_code, 403)
        guardar_permisos(self.u, {'inventario': 'editar'})
        self.assertContains(self.client.get(reverse('inventario:inicio')), '+ Registrar entrada')

    def test_configuracion_solo_ver_no_guarda(self):
        from apps.configuracion.models import Configuracion
        guardar_permisos(self.u, {'configuracion': 'ver'})
        self.assertContains(self.client.get(reverse('configuracion:inicio')), 'solo puede ver la configuración')
        self.client.post(reverse('configuracion:inicio'), {'nombre': 'Otro'})
        self.assertNotEqual(Configuracion.obtener().nombre, 'Otro')

    def test_ventas_solo_ver_no_anula_ni_cierra(self):
        guardar_permisos(self.u, {'ventas': 'ver'})
        self.assertEqual(self.client.get(reverse('ventas:cierre')).status_code, 200)
        self.assertEqual(self.client.post(reverse('ventas:cierre'), {'contado': '1'}).status_code, 403)

    def test_recibo_con_permiso_de_venta(self):
        from apps.ventas.servicios import registrar_venta
        v, _ = registrar_venta(usuario=self.u, lineas=[{'id': self.p.pk, 'cantidad': 1}], metodo='Tarjeta')
        guardar_permisos(self.u, {'inventario': 'ver'})
        self.assertEqual(self.client.get(reverse('ventas:recibo', args=[v.pk])).status_code, 403)
        guardar_permisos(self.u, {'venta_directa': 'editar'})
        self.assertEqual(self.client.get(reverse('ventas:recibo', args=[v.pk])).status_code, 200)

    def test_puede(self):
        guardar_permisos(self.u, {'mesas': 'ver'})
        self.assertTrue(puede(self.u, 'mesas'))
        self.assertFalse(puede(self.u, 'mesas', 'editar'))
        self.assertFalse(puede(self.u, 'ventas'))


class GestionUsuariosTests(TestCase):
    def setUp(self):
        self.duena = User.objects.create_superuser('duena', password='prueba-segura-123')
        self.cajero = User.objects.create_user('caja1', password='prueba-segura-123')
        guardar_permisos(self.cajero, PLANTILLA_CAJA)
        self.client.force_login(self.duena)

    def nuevo(self, permisos=None, **extra):
        d = {'username': 'maria', 'first_name': 'María Santos',
             'password1': 'Bebidas-2026!', 'password2': 'Bebidas-2026!', 'is_active': 'on'}
        for m, n in (permisos if permisos is not None else PLANTILLA_CAJA).items():
            d[f'perm_{m}'] = n
        d.update(extra)
        return self.client.post(reverse('usuarios:nuevo'), d)

    def test_crear_con_permisos_y_entrar(self):
        r = self.nuevo({'mesas': 'editar', 'ventas': 'ver'})
        self.assertRedirects(r, reverse('usuarios:inicio'))
        maria = User.objects.get(username='maria')
        self.assertEqual(permisos_de(maria), {'mesas': 'editar', 'ventas': 'ver'})
        self.client.logout()
        r = self.client.post(reverse('login'), {'username': 'maria', 'password': 'Bebidas-2026!'})
        self.assertRedirects(r, reverse('mesas:inicio'))
        self.assertEqual(self.client.get(reverse('inventario:inicio')).status_code, 403)

    def test_formulario_muestra_la_tabla_de_permisos(self):
        r = self.client.get(reverse('usuarios:nuevo'))
        self.assertContains(r, 'Permisos por módulo')
        self.assertContains(r, 'Ver y editar')
        self.assertContains(r, 'name="perm_configuracion"')

    def test_sin_ningun_modulo(self):
        self.assertContains(self.nuevo({}), 'Dale acceso al menos a un módulo', status_code=400)

    def test_validaciones(self):
        self.assertContains(self.nuevo(password2='otra-cosa-99'), 'Las contraseñas no coinciden.', status_code=400)
        self.assertEqual(self.nuevo(password1='123', password2='123').status_code, 400)
        self.assertContains(self.nuevo(username='CAJA1'), 'Ya existe un usuario con ese nombre.', status_code=400)

    def test_cambiar_permisos_de_usuario_existente(self):
        r = self.client.post(reverse('usuarios:editar', args=[self.cajero.pk]),
                             {'username': 'caja1', 'first_name': 'Caja', 'is_active': 'on', 'perm_ventas': 'editar', 'perm_mesas': 'ver'})
        self.assertRedirects(r, reverse('usuarios:inicio'))
        self.assertEqual(permisos_de(User.objects.get(pk=self.cajero.pk)), {'ventas': 'editar', 'mesas': 'ver'})

    def test_desactivar(self):
        self.client.post(reverse('usuarios:editar', args=[self.cajero.pk]), {'username': 'caja1', 'perm_mesas': 'ver'})
        self.cajero.refresh_from_db()
        self.assertFalse(self.cajero.is_active)
        self.client.logout()
        r = self.client.post(reverse('login'), {'username': 'caja1', 'password': 'prueba-segura-123'})
        self.assertEqual(r.status_code, 200)  # desactivado: no entra

    def test_no_cambia_sus_propios_permisos_ni_se_desactiva(self):
        jefe = User.objects.create_user('jefe', password='prueba-segura-123')
        guardar_permisos(jefe, {'usuarios': 'editar', 'ventas': 'editar'})
        self.client.force_login(jefe)
        self.client.post(reverse('usuarios:editar', args=[jefe.pk]), {'username': 'jefe', 'perm_configuracion': 'editar'})
        jefe = User.objects.get(pk=jefe.pk)
        self.assertTrue(jefe.is_active)
        self.assertEqual(permisos_de(jefe), {'usuarios': 'editar', 'ventas': 'editar'})

    def test_solo_el_dueno_toca_la_cuenta_del_dueno(self):
        jefe = User.objects.create_user('jefe', password='prueba-segura-123')
        guardar_permisos(jefe, {'usuarios': 'editar'})
        self.client.force_login(jefe)
        r = self.client.post(reverse('usuarios:clave', args=[self.duena.pk]), {'new_password1': 'Nueva-clave-55', 'new_password2': 'Nueva-clave-55'})
        self.assertRedirects(r, reverse('usuarios:inicio'))
        self.duena.refresh_from_db()
        self.assertFalse(self.duena.check_password('Nueva-clave-55'))

    def test_usuarios_solo_ver(self):
        jefe = User.objects.create_user('jefe', password='prueba-segura-123')
        guardar_permisos(jefe, {'usuarios': 'ver'})
        self.client.force_login(jefe)
        r = self.client.get(reverse('usuarios:inicio'))
        self.assertNotContains(r, '+ Nuevo usuario')
        self.assertEqual(self.nuevo().status_code, 403)

    def test_cambiar_contrasena(self):
        r = self.client.post(reverse('usuarios:clave', args=[self.cajero.pk]), {'new_password1': 'Nueva-clave-55', 'new_password2': 'Nueva-clave-55'})
        self.assertRedirects(r, reverse('usuarios:inicio'))
        self.cajero.refresh_from_db()
        self.assertTrue(self.cajero.check_password('Nueva-clave-55'))

    def test_cambiar_su_propia_contrasena_no_lo_saca(self):
        self.client.post(reverse('usuarios:clave', args=[self.duena.pk]), {'new_password1': 'Nueva-clave-55', 'new_password2': 'Nueva-clave-55'})
        self.assertEqual(self.client.get(reverse('usuarios:inicio')).status_code, 200)

    def test_cajero_no_maneja_usuarios(self):
        self.client.force_login(self.cajero)
        self.assertEqual(self.client.get(reverse('usuarios:nuevo')).status_code, 403)
        self.assertEqual(Permiso.objects.filter(usuario=self.cajero).count(), 3)
