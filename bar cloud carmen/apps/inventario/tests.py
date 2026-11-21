from django.contrib.auth.models import User
from django.test import TestCase

from apps.usuarios.permisos import PLANTILLA_CAJA, guardar_permisos
from django.urls import reverse

from apps.productos.models import Categoria, Producto
from apps.ventas.servicios import anular_venta, registrar_venta

from .models import Movimiento
from .servicios import lista_para_pedir


class InventarioTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('jefa', password='prueba-segura-123')
        self.cajero = User.objects.create_user('caja1', password='prueba-segura-123')
        guardar_permisos(self.cajero, PLANTILLA_CAJA)
        self.beb = Categoria.objects.get(nombre='Bebidas')
        self.cerveza = Producto.objects.create(nombre='Cerveza', categoria=self.beb, precio=150, costo=80, stock=30, stock_minimo=24)
        self.mojito = Producto.objects.create(nombre='Mojito', categoria=self.beb, precio=250, controla_stock=False)
        self.client.force_login(self.admin)

    def test_entrada_suma_actualiza_costo_y_guarda_movimiento(self):
        r = self.client.post(reverse('inventario:entrada'), {'producto': self.cerveza.pk, 'cantidad': '24', 'costo': '85', 'nota': 'pedido martes'})
        self.assertRedirects(r, reverse('inventario:inicio'))
        self.cerveza.refresh_from_db()
        self.assertEqual((self.cerveza.stock, self.cerveza.costo), (54, 85))
        m = Movimiento.objects.get()
        self.assertEqual((m.tipo, m.cantidad, m.stock_despues, m.nota, m.usuario), ('entrada', 24, 54, 'pedido martes', self.admin))

    def test_entrada_invalida(self):
        r = self.client.post(reverse('inventario:entrada'), {'producto': self.cerveza.pk, 'cantidad': '0'})
        self.assertContains(r, 'La cantidad debe ser mayor que cero.', status_code=400)
        r = self.client.post(reverse('inventario:entrada'), {'producto': self.mojito.pk, 'cantidad': '5'})
        self.assertContains(r, 'no controla inventario', status_code=400)
        self.assertFalse(Movimiento.objects.exists())

    def test_ajuste_por_conteo(self):
        r = self.client.post(reverse('inventario:ajuste', args=[self.cerveza.pk]), {'conteo': '27', 'motivo': 'Merma o rotura', 'nota': '3 rotas'})
        self.assertRedirects(r, reverse('inventario:inicio'))
        self.cerveza.refresh_from_db()
        self.assertEqual(self.cerveza.stock, 27)
        m = Movimiento.objects.get()
        self.assertEqual((m.tipo, m.cantidad, m.nota), ('ajuste', -3, 'Merma o rotura: 3 rotas'))

    def test_ajuste_sin_diferencia(self):
        r = self.client.post(reverse('inventario:ajuste', args=[self.cerveza.pk]), {'conteo': '30', 'motivo': 'Conteo físico'})
        self.assertContains(r, 'no hay nada que ajustar', status_code=400)

    def test_venta_y_anulacion_dejan_movimientos(self):
        v, _ = registrar_venta(usuario=self.cajero, lineas=[{'id': self.cerveza.pk, 'cantidad': 2}, {'id': self.mojito.pk, 'cantidad': 1}], metodo='Tarjeta')
        anular_venta(v, usuario=self.admin, motivo='error')
        movs = list(Movimiento.objects.order_by('pk').values_list('tipo', 'cantidad', 'stock_despues', 'venta_id'))
        self.assertEqual(movs, [('venta', -2, 28, v.pk), ('anulacion', 2, 30, v.pk)])

    def test_producto_nuevo_con_stock_inicial(self):
        self.client.post(reverse('productos:nuevo'), {
            'nombre': 'Ron', 'categoria': self.beb.pk, 'precio': '450', 'costo': '280',
            'stock_minimo': '3', 'stock_inicial': '8', 'controla_stock': 'on', 'activo': 'on'})
        m = Movimiento.objects.get(producto__nombre='Ron')
        self.assertEqual((m.tipo, m.cantidad, m.nota, m.costo), ('entrada', 8, 'Inventario inicial', 280))

    def test_existencias_resumen_y_lista_para_pedir(self):
        Producto.objects.create(nombre='Maní', categoria=self.beb, precio=50, costo=25, stock=0, stock_minimo=10)
        Producto.objects.filter(pk=self.cerveza.pk).update(stock=20)
        r = self.client.get(reverse('inventario:inicio'))
        self.assertEqual(r.context['resumen'], {'controlados': 2, 'bajos': 1, 'agotados': 1, 'valor': 1600})
        self.assertNotContains(r, 'Mojito')
        self.assertContains(r, '<span class="insignia" title="Productos con poco stock">2</span>', html=False)
        pedidos = {x['producto'].nombre: x['pedir'] for x in lista_para_pedir()}
        self.assertEqual(pedidos, {'Cerveza': 28, 'Maní': 20})
        self.assertContains(self.client.get(reverse('inventario:pedir_imprimir')), 'LISTA PARA PEDIR')

    def test_movimientos_filtro(self):
        self.client.post(reverse('inventario:entrada'), {'producto': self.cerveza.pk, 'cantidad': '5'})
        self.client.post(reverse('inventario:ajuste', args=[self.cerveza.pk]), {'conteo': '34', 'motivo': 'Conteo físico'})
        r = self.client.get(reverse('inventario:movimientos'), {'tipo': 'ajuste'})
        self.assertEqual([m.tipo for m in r.context['movimientos']], ['ajuste'])

    def test_cajero_no_entra(self):
        self.client.force_login(self.cajero)
        self.assertEqual(self.client.post(reverse('inventario:entrada'), {'producto': self.cerveza.pk, 'cantidad': '5'}).status_code, 403)
        r = self.client.get(reverse('venta_directa:inicio'))
        self.assertNotContains(r, 'class="insignia"')
