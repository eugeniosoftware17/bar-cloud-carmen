import json

from django.contrib.auth.models import User
from django.test import TestCase

from apps.usuarios.permisos import PLANTILLA_CAJA, guardar_permisos
from django.urls import reverse

from apps.inventario.models import Movimiento
from apps.productos.models import Categoria, Producto
from apps.ventas.models import Venta

from .models import Mesa, Mesera


class MesasTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('jefa', password='prueba-segura-123')
        self.cajero = User.objects.create_user('caja1', password='prueba-segura-123')
        guardar_permisos(self.cajero, PLANTILLA_CAJA)
        beb = Categoria.objects.get(nombre='Bebidas')
        self.cerveza = Producto.objects.create(nombre='Cerveza', categoria=beb, precio=150, stock=3)
        self.mojito = Producto.objects.create(nombre='Mojito', categoria=beb, precio=250, controla_stock=False)
        self.m1 = Mesa.objects.get(nombre='Mesa 1')
        self.m2 = Mesa.objects.get(nombre='Mesa 2')
        self.ana = Mesera.objects.create(nombre='Ana')
        self.client.force_login(self.cajero)

    def post(self, ruta, mesa=None, **datos):
        url = reverse(f'mesas:{ruta}', args=[mesa.pk]) if mesa else reverse(f'mesas:{ruta}')
        return self.client.post(url, json.dumps(datos), content_type='application/json')

    def abrir(self, mesa):
        r = self.post('abrir', mesa, mesera=self.ana.pk)
        self.assertTrue(r.json()['ok'], r.json())
        return r

    def test_ocho_mesas_iniciales(self):
        self.assertEqual(Mesa.objects.count(), 8)
        r = self.client.get(reverse('mesas:inicio'))
        self.assertContains(r, 'Mesa 8')
        self.assertEqual(r.context['frag']['libres'], 8)

    def test_abrir_agregar_y_quitar(self):
        self.abrir(self.m1)
        self.m1.refresh_from_db()
        self.assertTrue(self.m1.ocupada)
        self.assertEqual(self.m1.abierta_por, self.cajero)
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=1)
        r = self.post('consumo', self.m1, producto=self.cerveza.pk, delta=1)
        d = r.json()
        self.assertEqual(d['en_cuenta'], {str(self.cerveza.pk): 2})
        self.assertIn('RD$ 384', d['cuenta'])
        self.assertEqual(d['ocupadas'], 1)
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=-2)
        self.assertFalse(self.m1.consumos.exists())

    def test_abrir_pide_mesera(self):
        r = self.post('abrir', self.m1)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error'], 'Elige quién va a atender la mesa.')
        self.m1.refresh_from_db()
        self.assertFalse(self.m1.ocupada)

    def test_no_agrega_consumo_sin_abrir(self):
        r = self.post('consumo', self.m1, producto=self.mojito.pk, delta=1)
        self.assertEqual(r.status_code, 400)
        self.assertFalse(self.m1.consumos.exists())

    def test_abrir_con_mesera_nueva_la_guarda(self):
        r = self.post('abrir', self.m1, nombre='  carla   pérez ')
        d = r.json()
        self.assertTrue(d['ok'])
        self.assertEqual(self.m1.__class__.objects.get(pk=self.m1.pk).mesera.nombre, 'carla pérez')
        self.assertIn('carla pérez', [m['nombre'] for m in d['meseras']])
        self.assertIn('carla pérez', d['grid'])
        self.assertIn('carla pérez', d['cuenta'])
        # mismo nombre con otras mayúsculas: no se duplica
        self.post('abrir', self.m2, nombre='Carla Pérez')
        self.assertEqual(Mesera.objects.filter(nombre__iexact='carla pérez').count(), 1)

    def test_no_abre_dos_veces(self):
        self.abrir(self.m1)
        r = self.post('abrir', self.m1, mesera=self.ana.pk)
        self.assertEqual(r.status_code, 400)

    def test_cambiar_mesera(self):
        self.abrir(self.m1)
        luisa = Mesera.objects.create(nombre='Luisa')
        r = self.post('mesera', self.m1, mesera=luisa.pk)
        self.assertTrue(r.json()['ok'])
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.mesera, luisa)
        self.assertEqual(self.post('mesera', self.m2, mesera=luisa.pk).status_code, 400)

    def test_quitar_mesera_de_la_lista(self):
        self.abrir(self.m1)
        r = self.client.post(reverse('mesas:quitar_mesera', args=[self.ana.pk]))
        self.assertEqual(r.json()['meseras'], [])
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.mesera, self.ana)  # la mesa que ya atiende sigue igual
        self.assertEqual(self.post('abrir', self.m2, mesera=self.ana.pk).status_code, 400)
        # escribirla de nuevo la vuelve a activar
        self.post('abrir', self.m2, nombre='ana')
        self.assertTrue(Mesera.objects.get(pk=self.ana.pk).activa)

    def test_cajero_solo_ver_no_cambia_mesera(self):
        self.abrir(self.m1)
        guardar_permisos(self.cajero, {'mesas': 'ver'})
        self.client.force_login(User.objects.get(pk=self.cajero.pk))
        self.assertEqual(self.post('mesera', self.m1, mesera=self.ana.pk).status_code, 403)
        self.assertEqual(self.client.post(reverse('mesas:quitar_mesera', args=[self.ana.pk])).status_code, 403)

    def test_stock_apartado_entre_mesas(self):
        self.abrir(self.m1)
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=1)
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=1)
        self.abrir(self.m2)
        r = self.post('consumo', self.m2, producto=self.cerveza.pk, delta=1)
        self.assertTrue(r.json()['ok'])
        r = self.post('consumo', self.m2, producto=self.cerveza.pk, delta=1)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error'], 'Solo quedan 1 de Cerveza.')
        m3 = Mesa.objects.get(nombre='Mesa 3')
        self.abrir(m3)
        r = self.post('consumo', m3, producto=self.cerveza.pk, delta=1)
        self.assertIn('agotado', r.json()['error'])

    def test_no_descuenta_stock_hasta_cobrar(self):
        self.abrir(self.m1)
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=2)
        self.cerveza.refresh_from_db()
        self.assertEqual(self.cerveza.stock, 3)

    def test_cobrar_mesa(self):
        self.abrir(self.m1)
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=2)
        self.post('consumo', self.m1, producto=self.mojito.pk, delta=1)
        r = self.post('cobrar', self.m1, metodo='Efectivo', recibido=1000)
        d = r.json()
        self.assertTrue(d['ok'], d)
        v = Venta.objects.get(pk=d['venta']['id'])
        self.assertEqual((v.mesa, v.origen, v.subtotal, v.total), ('Mesa 1', 'Mesa 1', 550, 704))
        self.assertEqual((v.mesera, v.atendio), ('Ana', 'Ana'))
        self.m1.refresh_from_db(); self.cerveza.refresh_from_db()
        self.assertFalse(self.m1.ocupada)
        self.assertFalse(self.m1.consumos.exists())
        self.assertEqual(self.cerveza.stock, 1)
        self.assertEqual(Movimiento.objects.get().nota, f'Venta #{v.numero}')
        recibo = self.client.get(reverse('ventas:recibo', args=[v.pk]))
        self.assertContains(recibo, 'Mesa 1 · Venta')
        self.assertContains(recibo, '<span>Ana</span>')
        self.assertIsNone(self.m1.mesera)

    def test_cobrar_con_error_no_libera(self):
        self.abrir(self.m1)
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=1)
        r = self.post('cobrar', self.m1, metodo='Efectivo', recibido=10)
        self.assertEqual(r.status_code, 400)
        self.m1.refresh_from_db()
        self.assertTrue(self.m1.ocupada)
        self.assertEqual(self.m1.consumos.count(), 1)

    def test_cobrar_mesa_vacia(self):
        self.abrir(self.m1)
        self.assertEqual(self.post('cobrar', self.m1, metodo='Tarjeta').json()['error'], 'La mesa no tiene consumos.')

    def test_liberar_descarta(self):
        self.abrir(self.m1)
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=2)
        self.post('liberar', self.m1)
        self.m1.refresh_from_db()
        self.assertFalse(self.m1.ocupada)
        self.assertIsNone(self.m1.mesera)
        self.assertFalse(Venta.objects.exists())

    def test_precuenta(self):
        self.abrir(self.m1)
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=2)
        r = self.client.get(reverse('mesas:precuenta', args=[self.m1.pk]))
        self.assertContains(r, 'PRE-CUENTA')
        self.assertContains(r, '2 x Cerveza')
        self.assertContains(r, 'Le atiende')

    def test_agregar_mesa_pide_editar_mesas(self):
        guardar_permisos(self.cajero, {'mesas': 'ver'})
        self.assertEqual(self.post('nueva').status_code, 403)
        guardar_permisos(self.cajero, {'mesas': 'editar'})
        self.client.force_login(User.objects.get(pk=self.cajero.pk))
        r = self.post('nueva')
        self.assertEqual(r.json()['nombre'], 'Mesa 9')

    def test_pide_sesion(self):
        self.client.logout()
        self.assertEqual(self.post('abrir', self.m1).status_code, 302)
