"""Recibo: diseños, tamaño de letra, ancho del papel y copias en impresiones separadas."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.configuracion.models import Configuracion
from apps.productos.models import Categoria, Producto

from .servicios import registrar_venta


class ReciboTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('jefa', password='prueba-segura-123')
        beb = Categoria.objects.get(nombre='Bebidas')
        self.agua = Producto.objects.create(nombre='Agua', categoria=beb, precio=50, stock=20)
        self.venta, _ = registrar_venta(usuario=self.admin, metodo='Tarjeta', lineas=[{'id': self.agua.pk, 'cantidad': 2}])
        self.url = reverse('ventas:recibo', args=[self.venta.pk])
        self.client.force_login(self.admin)

    def conf(self, **campos):
        Configuracion.objects.filter(pk=Configuracion.obtener().pk).update(**campos)

    def test_por_defecto_no_fija_80mm_y_usa_el_ancho_de_la_impresora(self):
        r = self.client.get(self.url)
        html = r.content.decode()
        self.assertNotIn('size: 80mm', html)
        self.assertIn('width: 100%', html)
        self.assertIn('font-size: 14px', html)  # letra "Grande"
        self.assertIn('class="d-clasico"', html)

    def test_copias_separadas_imprime_una_y_luego_la_otra(self):
        r = self.client.get(self.url + '?imprimir=1')
        self.assertContains(r, 'COPIA CLIENTE')
        self.assertNotContains(r, 'COPIA NEGOCIO')
        self.assertContains(r, 'copia\\u003D2')  # la siguiente impresión es la copia del negocio
        r = self.client.get(self.url + '?imprimir=1&copia=2')
        self.assertContains(r, 'COPIA NEGOCIO')
        self.assertNotContains(r, 'COPIA CLIENTE')
        self.assertNotContains(r, 'location.replace')

    def test_copias_juntas_si_se_desmarca(self):
        self.conf(recibo_copias_separadas=False)
        r = self.client.get(self.url + '?imprimir=1')
        self.assertContains(r, 'COPIA CLIENTE')
        self.assertContains(r, 'COPIA NEGOCIO')
        self.assertNotContains(r, 'location.replace')

    def test_solo_copia_cliente(self):
        r = self.client.get(self.url + '?copias=1&imprimir=1')
        self.assertNotContains(r, 'COPIA')

    def test_disenos_letra_y_ancho(self):
        self.conf(recibo_diseno='detallado', recibo_letra='muy_grande', recibo_ancho='58')
        r = self.client.get(self.url)
        html = r.content.decode()
        self.assertIn('class="d-detallado"', html)
        self.assertIn('font-size: 16px', html)
        self.assertIn('width: 48mm', html)
        self.assertIn('2 x RD$ 50', html)  # el detallado muestra el precio de cada producto
        self.conf(recibo_diseno='moderno')
        self.assertContains(self.client.get(self.url), 'class="d-moderno"')

    def test_configuracion_guarda_y_muestra_vista_previa(self):
        r = self.client.get(reverse('configuracion:inicio'))
        self.assertContains(r, 'id="vistaRecibo"')
        r = self.client.get(reverse('configuracion:muestra_recibo'), {
            'nombre': 'La Patrona', 'recibo_diseno': 'moderno', 'recibo_letra': 'normal', 'recibo_ancho': 'auto',
            'propina_porcentaje': '10', 'itbis_porcentaje': '18', 'recibo_dos_copias': 'on'})
        self.assertContains(r, 'LA PATRONA')
        self.assertContains(r, 'class="d-moderno"')
        self.assertContains(r, 'COPIA NEGOCIO')
        self.assertEqual(Configuracion.obtener().recibo_diseno, 'clasico')  # la vista previa no guarda

    def test_precuenta_venta_directa_usa_el_diseno(self):
        self.conf(recibo_diseno='detallado')
        r = self.client.get(reverse('venta_directa:precuenta'), {'p': f'{self.agua.pk}:3,abc,999:1'})
        self.assertContains(r, 'PRE-CUENTA')
        self.assertContains(r, 'class="d-detallado"')
        self.assertContains(r, '3 x RD$ 50')
        self.assertContains(r, 'RD$ 150')
