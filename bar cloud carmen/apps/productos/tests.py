from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.usuarios.permisos import PLANTILLA_CAJA, guardar_permisos
from django.urls import reverse

from .models import Categoria, Producto
from .templatetags.productos import dinero


class ProductosTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('jefa', password='prueba-segura-123')
        self.cajero = User.objects.create_user('caja1', password='prueba-segura-123')
        guardar_permisos(self.cajero, PLANTILLA_CAJA)
        self.bebidas = Categoria.objects.get(nombre='Bebidas')
        self.comida = Categoria.objects.get(nombre='Comida')
        self.cerveza = Producto.objects.create(nombre='Cerveza Presidente', categoria=self.bebidas, precio=150, costo=80,
                                               stock=96, stock_minimo=24, dibujo='cerveza')

    def datos(self, **extra):
        d = {'nombre': 'Ron Brugal', 'categoria': self.bebidas.pk, 'dibujo': 'ron', 'color': '#7a3b12',
             'precio': '450', 'costo': '280', 'stock_minimo': '3', 'stock_inicial': '8',
             'controla_stock': 'on', 'activo': 'on'}
        d.update(extra)
        return d

    def test_categorias_iniciales(self):
        self.assertEqual(list(Categoria.objects.values_list('nombre', flat=True)), ['Bebidas', 'Comida', 'Snacks', 'Otros'])

    def test_estado_y_margen(self):
        self.assertEqual(self.cerveza.estado_stock, 'ok')
        self.cerveza.stock = 10
        self.assertEqual(self.cerveza.estado_stock, 'bajo')
        self.cerveza.stock = 0
        self.assertEqual(self.cerveza.estado_stock, 'agotado')
        self.cerveza.controla_stock = False
        self.assertEqual(self.cerveza.estado_stock, 'na')
        self.assertEqual(self.cerveza.margen, 47)

    def test_formato_dinero(self):
        self.assertEqual(dinero(Decimal('1088.00')), 'RD$ 1,088')
        self.assertEqual(dinero(0), 'RD$ 0')

    def test_admin_crea_producto_con_stock_inicial(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('productos:nuevo'), self.datos())
        self.assertRedirects(r, reverse('productos:inicio'))
        p = Producto.objects.get(nombre='Ron Brugal')
        self.assertEqual((p.precio, p.stock, p.stock_minimo), (450, 8, 3))

    def test_sin_control_de_stock_queda_en_cero(self):
        self.client.force_login(self.admin)
        datos = self.datos(nombre='Mojito', stock_inicial='20')
        del datos['controla_stock']
        self.client.post(reverse('productos:nuevo'), datos)
        self.assertEqual(Producto.objects.get(nombre='Mojito').stock, 0)

    def test_nombre_repetido_sin_importar_mayusculas(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('productos:nuevo'), self.datos(nombre='cerveza presidente'))
        self.assertContains(r, 'Ya existe un producto con ese nombre.', status_code=400)

    def test_precio_obligatorio(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('productos:nuevo'), self.datos(precio=''))
        self.assertContains(r, 'Escribe el precio de venta.', status_code=400)

    def test_editar_no_cambia_stock_y_puede_desactivar(self):
        self.client.force_login(self.admin)
        datos = self.datos(nombre='Cerveza Presidente', precio='175', stock_inicial='999')
        del datos['activo']
        r = self.client.post(reverse('productos:editar', args=[self.cerveza.pk]), datos)
        self.assertRedirects(r, reverse('productos:inicio'))
        self.cerveza.refresh_from_db()
        self.assertEqual((self.cerveza.precio, self.cerveza.stock, self.cerveza.activo), (175, 96, False))

    def test_volver_conserva_filtros_y_no_redirige_afuera(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('productos:nuevo'), self.datos(volver='?cat=1'))
        self.assertRedirects(r, reverse('productos:inicio') + '?cat=1')
        r = self.client.post(reverse('productos:nuevo'), self.datos(nombre='Otro', volver='https://ejemplo.com'))
        self.assertRedirects(r, reverse('productos:inicio'))

    def test_filtros(self):
        Producto.objects.create(nombre='Hamburguesa', categoria=self.comida, precio=380, controla_stock=False)
        Producto.objects.create(nombre='Maní', categoria=self.bebidas, precio=50, stock=0, stock_minimo=10)
        self.client.force_login(self.admin)
        url = reverse('productos:inicio')
        self.assertEqual([p.nombre for p in self.client.get(url, {'q': 'hambur'}).context['productos']], ['Hamburguesa'])
        self.assertEqual([p.nombre for p in self.client.get(url, {'cat': self.comida.pk}).context['productos']], ['Hamburguesa'])
        self.assertEqual([p.nombre for p in self.client.get(url, {'estado': 'bajo'}).context['productos']], ['Maní'])

    def test_cajero_consulta_sin_costos_y_no_edita(self):
        self.client.force_login(self.cajero)
        r = self.client.get(reverse('productos:inicio'))
        self.assertContains(r, 'Cerveza Presidente')
        self.assertNotContains(r, 'Margen')
        self.assertNotContains(r, '+ Nuevo producto')
        self.assertEqual(self.client.get(reverse('productos:nuevo')).status_code, 403)
        self.assertEqual(self.client.post(reverse('productos:editar', args=[self.cerveza.pk]), self.datos()).status_code, 403)

    def test_venta_directa_muestra_solo_activos(self):
        Producto.objects.create(nombre='Viejo', categoria=self.bebidas, precio=10, activo=False)
        self.client.force_login(self.cajero)
        r = self.client.get(reverse('venta_directa:inicio'))
        self.assertContains(r, 'Cerveza Presidente')
        self.assertContains(r, 'data-precio="150"')
        self.assertNotContains(r, 'Viejo')
