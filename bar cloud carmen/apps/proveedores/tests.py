from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.inventario.models import Movimiento
from apps.productos.models import Categoria, Producto
from apps.usuarios.permisos import guardar_permisos

from .models import Proveedor


class ProveedoresTests(TestCase):
    def setUp(self):
        self.duena = User.objects.create_superuser('duena', password='prueba-segura-123')
        self.cerveza = Producto.objects.create(nombre='Cerveza', categoria=Categoria.objects.get(nombre='Bebidas'),
                                               precio=150, costo=80, stock=10)
        self.cibao = Proveedor.objects.create(nombre='Distribuidora del Cibao', contacto='Pedro', telefono='809-555-0201', suple='cerveza')
        self.client.force_login(self.duena)

    def entrada(self, **extra):
        d = {'producto': self.cerveza.pk, 'cantidad': '24', 'costo': '85'}
        d.update(extra)
        return self.client.post(reverse('inventario:entrada'), d)

    def test_crear_y_editar(self):
        r = self.client.post(reverse('proveedores:nuevo'), {'nombre': 'Hielo Polar', 'telefono': '809-555-0203'})
        self.assertRedirects(r, reverse('proveedores:inicio'))
        p = Proveedor.objects.get(nombre='Hielo Polar')
        self.client.post(reverse('proveedores:editar', args=[p.pk]), {'nombre': 'Hielo Polar', 'suple': 'hielo en fundas'})
        p.refresh_from_db()
        self.assertEqual(p.suple, 'hielo en fundas')

    def test_nombre_repetido(self):
        r = self.client.post(reverse('proveedores:nuevo'), {'nombre': 'distribuidora del cibao'})
        self.assertContains(r, 'Ya existe un proveedor con ese nombre.', status_code=400)

    def test_entrada_con_proveedor_y_compras(self):
        self.assertRedirects(self.entrada(proveedor=self.cibao.pk), reverse('inventario:inicio'))
        m = Movimiento.objects.get()
        self.assertEqual(m.proveedor, self.cibao)
        r = self.client.get(reverse('proveedores:inicio'))
        fila = r.context['proveedores'].get(pk=self.cibao.pk)
        self.assertEqual(fila.compras, 24 * 85)
        self.assertIsNotNone(fila.ultima)
        self.assertContains(r, 'RD$ 2,040')
        self.assertContains(self.client.get(reverse('inventario:movimientos')), 'Distribuidora del Cibao')

    def test_entrada_sin_proveedor_y_con_uno_invalido(self):
        self.entrada()
        self.assertIsNone(Movimiento.objects.get().proveedor)
        r = self.entrada(proveedor='abc')
        self.assertContains(r, 'Ese proveedor ya no existe.', status_code=400)

    def test_eliminar_conserva_entradas(self):
        self.entrada(proveedor=self.cibao.pk)
        r = self.client.post(reverse('proveedores:eliminar', args=[self.cibao.pk]))
        self.assertRedirects(r, reverse('proveedores:inicio'))
        self.assertFalse(Proveedor.objects.exists())
        self.assertIsNone(Movimiento.objects.get().proveedor)

    def test_buscar(self):
        Proveedor.objects.create(nombre='Licores Santiago', suple='ron y licores')
        r = self.client.get(reverse('proveedores:inicio'), {'q': 'ron'})
        self.assertEqual([p.nombre for p in r.context['proveedores']], ['Licores Santiago'])

    def test_solo_ver(self):
        u = User.objects.create_user('ana', password='prueba-segura-123')
        guardar_permisos(u, {'proveedores': 'ver'})
        self.client.force_login(u)
        r = self.client.get(reverse('proveedores:inicio'))
        self.assertContains(r, 'Distribuidora del Cibao')
        self.assertNotContains(r, '+ Nuevo proveedor')
        self.assertEqual(self.client.post(reverse('proveedores:eliminar', args=[self.cibao.pk])).status_code, 403)
        self.assertTrue(Proveedor.objects.exists())
