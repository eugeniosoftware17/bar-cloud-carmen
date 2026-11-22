from django.contrib.auth.models import User
from django.test import TestCase

from apps.usuarios.permisos import PLANTILLA_CAJA, guardar_permisos
from django.urls import reverse

from apps.productos.models import Categoria, Producto
from apps.ventas.servicios import registrar_venta

from .models import Configuracion


class ConfiguracionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('jefa', password='prueba-segura-123')
        self.cajero = User.objects.create_user('caja1', password='prueba-segura-123')
        guardar_permisos(self.cajero, PLANTILLA_CAJA)
        self.cerveza = Producto.objects.create(nombre='Cerveza', categoria=Categoria.objects.get(nombre='Bebidas'),
                                               precio=150, stock=50)

    def datos(self, **extra):
        d = {'nombre': 'Bar de Carmen', 'direccion': 'Santiago', 'telefono': '809-555-0101',
             'cobrar_propina': 'on', 'propina_porcentaje': '10', 'cobrar_itbis': 'on', 'itbis_porcentaje': '18',
             'recibo_diseno': 'clasico', 'recibo_letra': 'grande', 'recibo_ancho': 'auto',
             'recibo_mostrar_atendio': 'on', 'recibo_mensaje': '¡Gracias por su visita!',
             'recibo_mostrar_aviso': 'on', 'recibo_aviso': 'Recibo interno · sin valor fiscal'}
        d.update(extra)
        return {k: v for k, v in d.items() if v is not None}

    def vender(self):
        v, _ = registrar_venta(usuario=self.cajero, lineas=[{'id': self.cerveza.pk, 'cantidad': 2}], metodo='Tarjeta')
        return v

    def test_solo_un_registro(self):
        a = Configuracion.obtener()
        a.save()
        Configuracion(nombre='Otro').save()
        self.assertEqual(Configuracion.objects.count(), 1)

    def test_solo_admin(self):
        self.client.force_login(self.cajero)
        self.assertEqual(self.client.get(reverse('configuracion:inicio')).status_code, 403)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('configuracion:inicio')), 'Vista previa del recibo')

    def test_guardar(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('configuracion:inicio'), self.datos())
        self.assertRedirects(r, reverse('configuracion:inicio'))
        self.assertEqual(Configuracion.obtener().nombre, 'Bar de Carmen')

    def test_porcentaje_invalido(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('configuracion:inicio'), self.datos(itbis_porcentaje='150'))
        self.assertEqual(r.status_code, 400)

    def test_quitar_propina_no_la_cobra_ni_la_imprime(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('configuracion:inicio'), self.datos(cobrar_propina=None))
        v = self.vender()
        self.assertEqual((v.subtotal, v.propina, v.itbis, v.total), (300, 0, 54, 354))
        r = self.client.get(reverse('ventas:recibo', args=[v.pk]))
        self.assertNotContains(r, 'Propina legal')
        self.assertContains(r, 'ITBIS')
        r = self.client.get(reverse('venta_directa:inicio'))
        self.assertContains(r, 'data-propina="0"')

    def test_quitar_textos_del_recibo(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('configuracion:inicio'), self.datos(recibo_mostrar_aviso=None, recibo_mensaje='', recibo_mostrar_atendio=None))
        r = self.client.get(reverse('ventas:recibo', args=[self.vender().pk]))
        self.assertNotContains(r, 'sin valor fiscal')
        self.assertNotContains(r, 'Gracias')
        self.assertNotContains(r, 'Atendió')
        self.assertContains(r, 'BAR DE CARMEN')
        self.assertContains(r, 'Tel. 809-555-0101')

    def test_ventas_viejas_conservan_su_propina(self):
        v = self.vender()
        self.client.force_login(self.admin)
        self.client.post(reverse('configuracion:inicio'), self.datos(cobrar_propina=None))
        r = self.client.get(reverse('ventas:recibo', args=[v.pk]))
        self.assertContains(r, 'Propina legal')
        self.assertContains(r, 'RD$ 384')
