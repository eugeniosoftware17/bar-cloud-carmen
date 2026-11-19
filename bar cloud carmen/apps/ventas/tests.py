import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.usuarios.permisos import PLANTILLA_CAJA, guardar_permisos
from django.urls import reverse

from apps.productos.models import Categoria, Producto

from .models import Venta
from .servicios import VentaError, anular_venta, calcular, registrar_venta


class VentasTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('jefa', password='prueba-segura-123')
        self.cajero = User.objects.create_user('caja1', password='prueba-segura-123')
        guardar_permisos(self.cajero, PLANTILLA_CAJA)
        beb = Categoria.objects.get(nombre='Bebidas')
        self.cerveza = Producto.objects.create(nombre='Cerveza', categoria=beb, precio=150, costo=80, stock=10, stock_minimo=8)
        self.ron = Producto.objects.create(nombre='Ron', categoria=beb, precio=450, costo=280, stock=2)
        self.mojito = Producto.objects.create(nombre='Mojito', categoria=beb, precio=250, controla_stock=False)

    def cobrar(self, usuario=None, **datos):
        self.client.force_login(usuario or self.cajero)
        datos.setdefault('metodo', 'Efectivo')
        return self.client.post(reverse('ventas:cobrar'), json.dumps(datos), content_type='application/json')

    # ---------- cálculos ----------
    def test_calculo_igual_que_el_diseno(self):
        t = calcular(Decimal('850'))
        self.assertEqual((t['propina'], t['itbis'], t['total']), (85, 153, 1088))

    # ---------- cobrar ----------
    def test_cobrar_en_efectivo_guarda_y_descuenta_stock(self):
        r = self.cobrar(lineas=[{'id': self.cerveza.pk, 'cantidad': 3}, {'id': self.mojito.pk, 'cantidad': 1}], recibido=1000)
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        v = Venta.objects.get(pk=d['venta']['id'])
        self.assertEqual((v.subtotal, v.propina, v.itbis, v.total), (700, 70, 126, 896))
        self.assertEqual((v.recibido, v.cambio, v.usuario), (1000, 104, self.cajero))
        self.assertEqual(v.lineas.count(), 2)
        self.cerveza.refresh_from_db(); self.mojito.refresh_from_db()
        self.assertEqual((self.cerveza.stock, self.mojito.stock), (7, 0))
        self.assertEqual(d['stock'], {str(self.cerveza.pk): 7})
        self.assertEqual(d['alertas'], ['Cerveza (7)'])

    def test_precio_lo_pone_el_servidor(self):
        r = self.cobrar(lineas=[{'id': self.cerveza.pk, 'cantidad': 1, 'precio': 1}], recibido=192)
        self.assertEqual(Venta.objects.get(pk=r.json()['venta']['id']).total, 192)

    def test_no_vende_mas_del_stock(self):
        r = self.cobrar(lineas=[{'id': self.ron.pk, 'cantidad': 3}], recibido=5000)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error'], 'Solo quedan 2 de Ron.')
        self.assertFalse(Venta.objects.exists())
        self.ron.refresh_from_db()
        self.assertEqual(self.ron.stock, 2)

    def test_efectivo_insuficiente(self):
        r = self.cobrar(lineas=[{'id': self.cerveza.pk, 'cantidad': 1}], recibido=100)
        self.assertEqual(r.json()['error'], 'El monto recibido es menor que el total.')

    def test_tarjeta_no_pide_monto(self):
        r = self.cobrar(lineas=[{'id': self.cerveza.pk, 'cantidad': 1}], metodo='Tarjeta', referencia='4321')
        v = Venta.objects.get(pk=r.json()['venta']['id'])
        self.assertEqual((v.recibido, v.cambio, v.referencia), (192, 0, '4321'))

    def test_errores_de_datos(self):
        self.assertEqual(self.cobrar(lineas=[]).json()['error'], 'La cuenta está vacía.')
        self.assertEqual(self.cobrar(lineas=[{'id': self.cerveza.pk, 'cantidad': 0}]).status_code, 400)
        self.assertEqual(self.cobrar(lineas=[{'id': self.cerveza.pk, 'cantidad': 1}], metodo='Cheque').status_code, 400)
        self.cerveza.activo = False; self.cerveza.save()
        self.assertEqual(self.cobrar(lineas=[{'id': self.cerveza.pk, 'cantidad': 1}], recibido=999).status_code, 400)

    def test_cobrar_pide_sesion_y_post(self):
        r = self.client.post(reverse('ventas:cobrar'), '{}', content_type='application/json')
        self.assertEqual(r.status_code, 302)
        self.client.force_login(self.cajero)
        self.assertEqual(self.client.get(reverse('ventas:cobrar')).status_code, 405)

    # ---------- recibo ----------
    def test_recibo(self):
        v, _ = registrar_venta(usuario=self.cajero, lineas=[{'id': self.cerveza.pk, 'cantidad': 2}], metodo='Efectivo', recibido=500)
        self.client.force_login(self.cajero)
        r = self.client.get(reverse('ventas:recibo', args=[v.pk]))
        self.assertContains(r, f'Venta #{v.numero}')
        self.assertContains(r, '2 x Cerveza')
        self.assertContains(r, 'RD$ 384')
        self.assertContains(r, 'RD$ 116')  # cambio

    # ---------- anular ----------
    def test_anular_devuelve_stock(self):
        v, _ = registrar_venta(usuario=self.cajero, lineas=[{'id': self.ron.pk, 'cantidad': 2}, {'id': self.mojito.pk, 'cantidad': 1}], metodo='Tarjeta')
        self.ron.refresh_from_db(); self.assertEqual(self.ron.stock, 0)
        self.client.force_login(self.admin)
        r = self.client.post(reverse('ventas:anular', args=[v.pk]), {'motivo': 'Se cobró dos veces'})
        self.assertRedirects(r, reverse('ventas:inicio'))
        v.refresh_from_db(); self.ron.refresh_from_db(); self.mojito.refresh_from_db()
        self.assertTrue(v.anulada)
        self.assertEqual((v.anulada_por, v.motivo_anulacion), (self.admin, 'Se cobró dos veces'))
        self.assertEqual((self.ron.stock, self.mojito.stock), (2, 0))
        with self.assertRaises(VentaError):
            anular_venta(v, usuario=self.admin, motivo='otra vez')
        self.ron.refresh_from_db(); self.assertEqual(self.ron.stock, 2)

    def test_anular_pide_motivo(self):
        v, _ = registrar_venta(usuario=self.cajero, lineas=[{'id': self.ron.pk, 'cantidad': 1}], metodo='Tarjeta')
        self.client.force_login(self.admin)
        r = self.client.post(reverse('ventas:anular', args=[v.pk]), {'motivo': '  '})
        self.assertContains(r, 'Escribe el motivo.', status_code=400)
        v.refresh_from_db(); self.assertFalse(v.anulada)

    def test_cajero_no_ve_historial_ni_anula(self):
        v, _ = registrar_venta(usuario=self.cajero, lineas=[{'id': self.ron.pk, 'cantidad': 1}], metodo='Tarjeta')
        self.client.force_login(self.cajero)
        self.assertEqual(self.client.get(reverse('ventas:inicio')).status_code, 403)
        self.assertEqual(self.client.post(reverse('ventas:anular', args=[v.pk]), {'motivo': 'x'}).status_code, 403)
        v.refresh_from_db(); self.assertFalse(v.anulada)

    # ---------- historial ----------
    def test_historial_resumen_y_filtros(self):
        a, _ = registrar_venta(usuario=self.cajero, lineas=[{'id': self.cerveza.pk, 'cantidad': 1}], metodo='Efectivo', recibido=192)
        b, _ = registrar_venta(usuario=self.cajero, lineas=[{'id': self.mojito.pk, 'cantidad': 2}], metodo='Tarjeta')
        anular_venta(a, usuario=self.admin, motivo='prueba')
        self.client.force_login(self.admin)
        r = self.client.get(reverse('ventas:inicio'), {'per': '0'})
        self.assertEqual(r.context['resumen']['validas']['total'], b.total)
        self.assertEqual(r.context['resumen']['anuladas']['n'], 1)
        r = self.client.get(reverse('ventas:inicio'), {'metodo': 'Tarjeta'})
        self.assertEqual(list(r.context['ventas']), [b])
        r = self.client.get(reverse('ventas:inicio'), {'num': f'#{a.numero}'})
        self.assertEqual(list(r.context['ventas']), [a])
        r = self.client.get(reverse('ventas:detalle', args=[b.pk]))
        self.assertContains(r, '2 x Mojito')
