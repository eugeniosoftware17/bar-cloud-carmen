import json

from django.contrib.auth.models import User
from django.test import TestCase

from apps.usuarios.permisos import PLANTILLA_CAJA, guardar_permisos
from django.urls import reverse

from apps.inventario.models import Movimiento
from apps.productos.models import Categoria, Producto
from apps.ventas.models import Venta

from .models import Mesa


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
        self.client.force_login(self.cajero)

    def post(self, nombre, mesa=None, **datos):
        url = reverse(f'mesas:{nombre}', args=[mesa.pk]) if mesa else reverse(f'mesas:{nombre}')
        return self.client.post(url, json.dumps(datos), content_type='application/json')

    def test_ocho_mesas_iniciales(self):
        self.assertEqual(Mesa.objects.count(), 8)
        r = self.client.get(reverse('mesas:inicio'))
        self.assertContains(r, 'Mesa 8')
        self.assertEqual(r.context['frag']['libres'], 8)

    def test_abrir_agregar_y_quitar(self):
        r = self.post('abrir', self.m1)
        self.assertTrue(r.json()['ok'])
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

    def test_agregar_abre_la_mesa_sola(self):
        self.post('consumo', self.m1, producto=self.mojito.pk, delta=1)
        self.m1.refresh_from_db()
        self.assertTrue(self.m1.ocupada)

    def test_stock_apartado_entre_mesas(self):
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=1)
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=1)
        r = self.post('consumo', self.m2, producto=self.cerveza.pk, delta=1)
        self.assertTrue(r.json()['ok'])
        r = self.post('consumo', self.m2, producto=self.cerveza.pk, delta=1)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error'], 'Solo quedan 1 de Cerveza.')
        r = self.post('consumo', Mesa.objects.get(nombre='Mesa 3'), producto=self.cerveza.pk, delta=1)
        self.assertIn('agotado', r.json()['error'])

    def test_no_descuenta_stock_hasta_cobrar(self):
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=2)
        self.cerveza.refresh_from_db()
        self.assertEqual(self.cerveza.stock, 3)

    def test_cobrar_mesa(self):
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=2)
        self.post('consumo', self.m1, producto=self.mojito.pk, delta=1)
        r = self.post('cobrar', self.m1, metodo='Efectivo', recibido=1000)
        d = r.json()
        self.assertTrue(d['ok'], d)
        v = Venta.objects.get(pk=d['venta']['id'])
        self.assertEqual((v.mesa, v.origen, v.subtotal, v.total), ('Mesa 1', 'Mesa 1', 550, 704))
        self.m1.refresh_from_db(); self.cerveza.refresh_from_db()
        self.assertFalse(self.m1.ocupada)
        self.assertFalse(self.m1.consumos.exists())
        self.assertEqual(self.cerveza.stock, 1)
        self.assertEqual(Movimiento.objects.get().nota, f'Venta #{v.numero}')
        self.assertContains(self.client.get(reverse('ventas:recibo', args=[v.pk])), 'Mesa 1 · Venta')

    def test_cobrar_con_error_no_libera(self):
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=1)
        r = self.post('cobrar', self.m1, metodo='Efectivo', recibido=10)
        self.assertEqual(r.status_code, 400)
        self.m1.refresh_from_db()
        self.assertTrue(self.m1.ocupada)
        self.assertEqual(self.m1.consumos.count(), 1)

    def test_cobrar_mesa_vacia(self):
        self.post('abrir', self.m1)
        self.assertEqual(self.post('cobrar', self.m1, metodo='Tarjeta').json()['error'], 'La mesa no tiene consumos.')

    def test_liberar_descarta(self):
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=2)
        self.post('liberar', self.m1)
        self.m1.refresh_from_db()
        self.assertFalse(self.m1.ocupada)
        self.assertFalse(Venta.objects.exists())

    def test_precuenta(self):
        self.post('consumo', self.m1, producto=self.cerveza.pk, delta=2)
        r = self.client.get(reverse('mesas:precuenta', args=[self.m1.pk]))
        self.assertContains(r, 'PRE-CUENTA')
        self.assertContains(r, '2 x Cerveza')

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
