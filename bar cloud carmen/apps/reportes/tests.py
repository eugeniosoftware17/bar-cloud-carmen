from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.productos.models import Categoria, Producto
from apps.usuarios.permisos import guardar_permisos
from apps.ventas.models import Venta
from apps.ventas.servicios import anular_venta, registrar_venta

from . import calculos
from .models import Gasto


class ReportesTests(TestCase):
    def setUp(self):
        self.duena = User.objects.create_superuser('duena', password='prueba-segura-123')
        beb = Categoria.objects.get(nombre='Bebidas')
        self.cerveza = Producto.objects.create(nombre='Cerveza', categoria=beb, precio=150, costo=80, stock=100)
        self.ron = Producto.objects.create(nombre='Ron', categoria=beb, precio=450, costo=280, stock=100)
        self.agua = Producto.objects.create(nombre='Agua', categoria=beb, precio=50, costo=20, stock=100)
        self.hoy = timezone.localdate()
        # hoy: 3 cervezas (efectivo) + 1 ron (tarjeta); una anulada que no cuenta
        registrar_venta(usuario=self.duena, lineas=[{'id': self.cerveza.pk, 'cantidad': 3}], metodo='Efectivo', recibido=1000)
        registrar_venta(usuario=self.duena, lineas=[{'id': self.ron.pk, 'cantidad': 1}], metodo='Tarjeta')
        v, _ = registrar_venta(usuario=self.duena, lineas=[{'id': self.ron.pk, 'cantidad': 5}], metodo='Tarjeta')
        anular_venta(v, usuario=self.duena, motivo='prueba')
        self.client.force_login(self.duena)

    def test_estadisticas(self):
        e = calculos.estadisticas('7', 'dia')
        self.assertEqual((e['neto'], e['n'], e['promedio'], e['bruta']), (900, 2, 450, 900 - 240 - 280))
        self.assertEqual([(x['n'], x['q']) for x in e['mas'][:2]], [('Cerveza', 3), ('Ron', 1)])
        self.assertEqual(e['menos'][0], {'n': 'Agua', 'q': 0, 'porc': 0})
        self.assertEqual(len(e['serie']), 14)
        self.assertEqual(e['serie'][-1]['v'], 900)
        self.assertEqual(e['pico']['v'], 2)
        tarjeta = next(m for m in e['metodos'] if m['m'] == 'Tarjeta')
        self.assertEqual(tarjeta['total'], 576)

    def test_ventas_por_mesera(self):
        self.assertEqual(calculos.estadisticas('7')['meseras'], [])
        registrar_venta(usuario=self.duena, lineas=[{'id': self.ron.pk, 'cantidad': 2}], metodo='Tarjeta', mesa='Mesa 1', mesera='Ana')
        registrar_venta(usuario=self.duena, lineas=[{'id': self.cerveza.pk, 'cantidad': 1}], metodo='Tarjeta', mesa='Mesa 2', mesera='Ana')
        registrar_venta(usuario=self.duena, lineas=[{'id': self.agua.pk, 'cantidad': 1}], metodo='Tarjeta', mesa='Mesa 3', mesera='Luisa')
        m = calculos.estadisticas('7')['meseras']
        self.assertEqual([(x['mesera'], x['cuentas'], x['neto'], x['propina']) for x in m],
                         [('Ana', 2, 1050, 105), ('Luisa', 1, 50, 5)])
        self.assertContains(self.client.get(reverse('reportes:inicio')), 'Por mesera')

    def test_series_por_semana_y_mes(self):
        self.assertEqual(len(calculos.serie_ventas('semana')), 8)
        mes = calculos.serie_ventas('mes')
        self.assertEqual(len(mes), 6)
        self.assertEqual(mes[-1]['v'], 900)

    def test_venta_vieja_fuera_del_rango(self):
        v = Venta.objects.filter(anulada=False).first()
        Venta.objects.filter(pk=v.pk).update(fecha=timezone.now() - timedelta(days=40))
        self.assertEqual(calculos.estadisticas('30')['n'], 1)

    def test_pagina_estadisticas(self):
        r = self.client.get(reverse('reportes:inicio'), {'rango': '1', 'gran': 'semana'})
        self.assertContains(r, 'Productos que más se venden')
        self.assertContains(r, 'RD$ 900')
        self.assertContains(r, 'semana (8 semanas)')

    def test_gastos_y_ganancia_neta(self):
        r = self.client.post(reverse('reportes:gasto_nuevo'), {'concepto': 'Luz', 'monto': '300', 'fecha': self.hoy.isoformat(), 'categoria': 'Servicios'})
        self.assertRedirects(r, reverse('reportes:ganancias') + f'?mes={self.hoy:%Y-%m}')
        self.assertEqual(Gasto.objects.get().usuario, self.duena)
        g = calculos.ganancias(self.hoy.year, self.hoy.month)
        self.assertEqual((g['neto'], g['costo'], g['bruta'], g['gastos_total'], g['neta']), (900, 520, 380, 300, 80))
        self.assertEqual(g['porc_neta'], 9)
        r = self.client.get(reverse('reportes:ganancias'), {'mes': f'{self.hoy:%Y-%m}'})
        self.assertContains(r, 'Luz')
        self.assertContains(r, 'no son ingreso del negocio')

    def test_ganancia_negativa(self):
        Gasto.objects.create(concepto='Alquiler', monto=5000, categoria='Alquiler', usuario=self.duena)
        r = self.client.get(reverse('reportes:ganancias'))
        self.assertContains(r, '−RD$ 4,620')

    def test_gasto_validaciones(self):
        manana = (self.hoy + timedelta(days=1)).isoformat()
        r = self.client.post(reverse('reportes:gasto_nuevo'), {'concepto': 'X', 'monto': '10', 'fecha': manana, 'categoria': 'Otros'})
        self.assertContains(r, 'La fecha no puede ser futura.', status_code=400)
        r = self.client.post(reverse('reportes:gasto_nuevo'), {'concepto': '', 'monto': '', 'fecha': self.hoy.isoformat(), 'categoria': 'Otros'})
        self.assertContains(r, 'Escribe el concepto.', status_code=400)

    def test_editar_y_eliminar_gasto(self):
        x = Gasto.objects.create(concepto='Hielo', monto=200, categoria='Insumos', usuario=self.duena)
        self.client.post(reverse('reportes:gasto_editar', args=[x.pk]), {'concepto': 'Hielo', 'monto': '250', 'fecha': self.hoy.isoformat(), 'categoria': 'Insumos'})
        x.refresh_from_db()
        self.assertEqual(x.monto, 250)
        self.client.post(reverse('reportes:gasto_eliminar', args=[x.pk]))
        self.assertFalse(Gasto.objects.exists())

    def test_mes_invalido_usa_el_actual(self):
        r = self.client.get(reverse('reportes:ganancias'), {'mes': 'abc'})
        self.assertEqual(r.context['mes'], f'{self.hoy:%Y-%m}')

    def test_solo_ver_no_registra_gastos(self):
        u = User.objects.create_user('ana', password='prueba-segura-123')
        guardar_permisos(u, {'reportes': 'ver'})
        self.client.force_login(u)
        r = self.client.get(reverse('reportes:ganancias'))
        self.assertNotContains(r, '+ Registrar gasto')
        r = self.client.post(reverse('reportes:gasto_nuevo'), {'concepto': 'X', 'monto': '10', 'fecha': self.hoy.isoformat(), 'categoria': 'Otros'})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Gasto.objects.exists())
