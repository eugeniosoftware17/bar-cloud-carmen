from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from apps.usuarios.permisos import PLANTILLA_CAJA, guardar_permisos
from django.urls import reverse
from django.utils import timezone

from apps.productos.models import Categoria, Producto

from .cierre import resumen_dia
from .models import CierreCaja
from .servicios import anular_venta, registrar_venta


class CierreTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('jefa', password='prueba-segura-123')
        self.cajero = User.objects.create_user('caja1', password='prueba-segura-123')
        guardar_permisos(self.cajero, PLANTILLA_CAJA)
        beb = Categoria.objects.get(nombre='Bebidas')
        self.cerveza = Producto.objects.create(nombre='Cerveza', categoria=beb, precio=150, stock=100)
        self.ron = Producto.objects.create(nombre='Ron', categoria=beb, precio=450, stock=100)
        self.hoy = timezone.localdate()
        # efectivo 384 (2 cervezas) + tarjeta 576 (1 ron) + una anulada
        registrar_venta(usuario=self.cajero, lineas=[{'id': self.cerveza.pk, 'cantidad': 2}], metodo='Efectivo', recibido=500)
        registrar_venta(usuario=self.cajero, lineas=[{'id': self.ron.pk, 'cantidad': 1}], metodo='Tarjeta')
        v, _ = registrar_venta(usuario=self.cajero, lineas=[{'id': self.cerveza.pk, 'cantidad': 1}], metodo='Efectivo', recibido=192)
        anular_venta(v, usuario=self.admin, motivo='prueba')
        self.client.force_login(self.admin)

    def test_resumen(self):
        r = resumen_dia(self.hoy)
        self.assertEqual((r['num_ventas'], r['total'], r['neto'], r['efectivo']), (2, 960, 750, 384))
        self.assertEqual((r['anuladas_n'], r['anuladas_total']), (1, 192))
        self.assertEqual([(p['nombre'], p['cantidad']) for p in r['top']], [('Cerveza', 2), ('Ron', 1)])
        tarjeta = next(m for m in r['por_metodo'] if m['metodo'] == 'Tarjeta')
        self.assertEqual((tarjeta['n'], tarjeta['total']), (1, 576))

    def test_cerrar_dia(self):
        r = self.client.post(reverse('ventas:cierre'), {'dia': self.hoy.isoformat(), 'fondo': '2000', 'contado': '2334', 'nota': 'faltan 50'})
        self.assertRedirects(r, reverse('ventas:cierre') + f'?dia={self.hoy.isoformat()}')
        c = CierreCaja.objects.get(dia=self.hoy)
        self.assertEqual((c.esperado, c.contado, c.diferencia, c.resultado), (2384, 2334, -50, 'Falta'))
        self.assertEqual((c.total_vendido, c.usuario), (960, self.admin))

    def test_actualizar_no_duplica(self):
        url = reverse('ventas:cierre')
        self.client.post(url, {'dia': self.hoy.isoformat(), 'fondo': '0', 'contado': '384'})
        self.client.post(url, {'dia': self.hoy.isoformat(), 'fondo': '0', 'contado': '400'})
        self.assertEqual(CierreCaja.objects.count(), 1)
        self.assertEqual(CierreCaja.objects.get().resultado, 'Sobra')

    def test_pide_contado(self):
        r = self.client.post(reverse('ventas:cierre'), {'dia': self.hoy.isoformat(), 'fondo': '2000', 'contado': ''})
        self.assertContains(r, 'Escribe el efectivo contado', status_code=400)
        self.assertFalse(CierreCaja.objects.exists())

    def test_aviso_si_hubo_ventas_despues(self):
        self.client.post(reverse('ventas:cierre'), {'dia': self.hoy.isoformat(), 'fondo': '0', 'contado': '384'})
        registrar_venta(usuario=self.cajero, lineas=[{'id': self.cerveza.pk, 'cantidad': 1}], metodo='Efectivo', recibido=192)
        r = self.client.get(reverse('ventas:cierre'))
        self.assertContains(r, 'Hubo ventas o anulaciones después de cerrar')

    def test_dia_futuro_usa_hoy(self):
        manana = (self.hoy + timedelta(days=1)).isoformat()
        r = self.client.get(reverse('ventas:cierre'), {'dia': manana})
        self.assertEqual(r.context['dia'], self.hoy)

    def test_otro_dia_sin_ventas(self):
        ayer = (self.hoy - timedelta(days=1)).isoformat()
        self.assertContains(self.client.get(reverse('ventas:cierre'), {'dia': ayer}), 'No hay ventas en esta fecha')

    def test_imprimir(self):
        r = self.client.get(reverse('ventas:cierre_imprimir'), {'dia': self.hoy.isoformat(), 'fondo': '2000', 'contado': '2384'})
        self.assertContains(r, 'CIERRE DEL DÍA')
        self.assertContains(r, 'CUADRA')
        self.assertContains(r, 'RD$ 2,384')

    def test_cajero_no_cierra(self):
        self.client.force_login(self.cajero)
        self.assertEqual(self.client.get(reverse('ventas:cierre')).status_code, 403)
        self.assertEqual(self.client.post(reverse('ventas:cierre'), {'contado': '1'}).status_code, 403)
