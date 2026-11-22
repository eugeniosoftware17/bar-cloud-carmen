"""Eliminar productos creados por error (solo si no tienen ventas ni están en uso)."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.inventario.models import Movimiento
from apps.inventario.servicios import registrar_entrada
from apps.mesas.models import Consumo, Mesa, Mesera
from apps.usuarios.permisos import PLANTILLA_CAJA, guardar_permisos
from apps.ventas.servicios import registrar_venta

from .models import Categoria, ComboItem, Producto


class EliminarProductoTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('jefa', password='prueba-segura-123')
        self.beb = Categoria.objects.get(nombre='Bebidas')
        self.malo = Producto.objects.create(nombre='Presidnete', categoria=self.beb, precio=200, costo=110)
        registrar_entrada(producto_id=self.malo.pk, cantidad=24, usuario=self.admin, nota='Inventario inicial')
        self.client.force_login(self.admin)

    def url(self, p):
        return reverse('productos:eliminar', args=[p.pk])

    def test_elimina_producto_sin_ventas_con_sus_movimientos(self):
        r = self.client.get(self.url(self.malo))
        self.assertContains(r, 'Se elimina <b>Presidnete</b> junto con sus 24 unidades')
        r = self.client.post(self.url(self.malo), {'volver': '?q=pres'})
        self.assertRedirects(r, reverse('productos:inicio') + '?q=pres', fetch_redirect_response=False)
        self.assertFalse(Producto.objects.filter(pk=self.malo.pk).exists())
        self.assertFalse(Movimiento.objects.exists())

    def test_no_elimina_producto_vendido(self):
        registrar_venta(usuario=self.admin, metodo='Tarjeta', lineas=[{'id': self.malo.pk, 'cantidad': 1}])
        r = self.client.post(self.url(self.malo))
        self.assertContains(r, 'ya se vendió (1 venta)', status_code=400)
        self.assertNotContains(r, '<button class="btn prim" type="submit">Eliminar</button>', status_code=400, html=True)
        self.assertTrue(Producto.objects.filter(pk=self.malo.pk).exists())

    def test_no_elimina_producto_en_mesa_o_en_combo(self):
        mesa = Mesa.objects.get(nombre='Mesa 1')
        mesa.mesera = Mesera.objects.create(nombre='Ana')
        Consumo.objects.create(mesa=mesa, producto=self.malo, cantidad=1)
        self.assertContains(self.client.post(self.url(self.malo)), 'cuenta abierta (Mesa 1)', status_code=400)
        Consumo.objects.all().delete()
        combo = Producto.objects.create(nombre='Cubeta', categoria=self.beb, precio=900, es_combo=True, controla_stock=False)
        ComboItem.objects.create(combo=combo, producto=self.malo, cantidad=5)
        self.assertContains(self.client.post(self.url(self.malo)), 'forma parte del combo Cubeta', status_code=400)
        # el combo sí se puede eliminar (sus productos quedan)
        self.client.post(self.url(combo))
        self.assertFalse(Producto.objects.filter(pk=combo.pk).exists())
        self.assertTrue(Producto.objects.filter(pk=self.malo.pk).exists())

    def test_boton_en_editar_y_permisos(self):
        r = self.client.get(reverse('productos:editar', args=[self.malo.pk]))
        self.assertContains(r, self.url(self.malo))
        cajero = User.objects.create_user('caja1', password='prueba-segura-123')
        guardar_permisos(cajero, PLANTILLA_CAJA)  # productos: solo ver
        self.client.force_login(cajero)
        self.assertEqual(self.client.post(self.url(self.malo)).status_code, 403)
        self.assertTrue(Producto.objects.filter(pk=self.malo.pk).exists())
