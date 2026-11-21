"""Combos: un producto que se arma con otros y descuenta del inventario lo que lleva."""

import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.inventario.models import Movimiento
from apps.inventario.servicios import registrar_entrada
from apps.mesas.models import Mesa, Mesera
from apps.usuarios.permisos import PLANTILLA_CAJA, guardar_permisos
from apps.ventas.models import Venta
from apps.ventas.servicios import VentaError, anular_venta, registrar_venta

from .models import Categoria, ComboItem, Producto


class CombosTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('jefa', password='prueba-segura-123')
        self.cajero = User.objects.create_user('caja1', password='prueba-segura-123')
        guardar_permisos(self.cajero, PLANTILLA_CAJA)
        self.beb = Categoria.objects.get(nombre='Bebidas')
        self.cerveza = Producto.objects.create(nombre='Presidente', categoria=self.beb, precio=200, costo=110, stock=12, stock_minimo=6)
        self.hielo = Producto.objects.create(nombre='Hielo', categoria=self.beb, precio=50, costo=20, stock=50)
        self.limon = Producto.objects.create(nombre='Limón', categoria=self.beb, precio=10, controla_stock=False)
        self.cubeta = Producto.objects.create(nombre='Cubeta 5 Presidente', categoria=self.beb, precio=900,
                                              es_combo=True, controla_stock=False, costo=570)
        ComboItem.objects.create(combo=self.cubeta, producto=self.cerveza, cantidad=5)
        ComboItem.objects.create(combo=self.cubeta, producto=self.hielo, cantidad=1)

    def vender(self, *lineas, metodo='Tarjeta'):
        return registrar_venta(usuario=self.cajero, metodo=metodo,
                               lineas=[{'id': p.pk, 'cantidad': n} for p, n in lineas])

    def recargar(self, *ps):
        for p in ps:
            p.refresh_from_db()

    # ---------- disponibles ----------
    def test_disponibles_segun_el_producto_que_se_acaba_primero(self):
        self.assertEqual(self.cubeta.disponibles, 2)  # 12 cervezas / 5
        self.assertEqual(self.cubeta.estado_stock, 'ok')
        Producto.objects.filter(pk=self.cerveza.pk).update(stock=4)
        self.assertEqual(Producto.objects.get(pk=self.cubeta.pk).estado_stock, 'agotado')

    def test_combo_solo_con_productos_sin_control_no_tiene_limite(self):
        combo = Producto.objects.create(nombre='Limonada', categoria=self.beb, precio=100, es_combo=True, controla_stock=False)
        ComboItem.objects.create(combo=combo, producto=self.limon, cantidad=3)
        self.assertIsNone(combo.disponibles)
        self.assertEqual(combo.stock_js, -1)

    # ---------- vender y anular ----------
    def test_vender_combo_descuenta_sus_productos(self):
        venta, alertas = self.vender((self.cubeta, 2))
        self.recargar(self.cerveza, self.hielo, self.cubeta)
        self.assertEqual((self.cerveza.stock, self.hielo.stock, self.cubeta.stock), (2, 48, 0))
        linea = venta.lineas.get()
        self.assertEqual((linea.nombre, linea.cantidad, linea.precio, linea.costo), ('Cubeta 5 Presidente', 2, 900, 570))
        notas = set(Movimiento.objects.values_list('nota', flat=True))
        self.assertEqual(notas, {f'Venta #{venta.numero} · Combo: Cubeta 5 Presidente'})
        self.assertEqual(alertas, [self.cerveza])

    def test_combo_y_suelto_en_la_misma_venta_suman(self):
        self.vender((self.cubeta, 1), (self.cerveza, 3))
        self.recargar(self.cerveza)
        self.assertEqual(self.cerveza.stock, 4)
        self.assertEqual(Movimiento.objects.get(producto=self.cerveza).cantidad, -8)

    def test_no_vende_combo_si_no_alcanza(self):
        with self.assertRaisesMessage(VentaError, 'No alcanza Presidente para el combo Cubeta 5 Presidente: solo quedan 12.'):
            self.vender((self.cubeta, 3))
        with self.assertRaisesMessage(VentaError, 'No alcanza Presidente'):
            self.vender((self.cubeta, 2), (self.cerveza, 3))
        self.assertFalse(Venta.objects.exists())
        self.recargar(self.cerveza)
        self.assertEqual(self.cerveza.stock, 12)

    def test_combo_vacio_no_se_vende(self):
        vacio = Producto.objects.create(nombre='Combo vacío', categoria=self.beb, precio=100, es_combo=True, controla_stock=False)
        with self.assertRaisesMessage(VentaError, 'no tiene productos'):
            self.vender((vacio, 1))

    def test_anular_devuelve_lo_que_salio_aunque_el_combo_cambie(self):
        venta, _ = self.vender((self.cubeta, 1))
        ComboItem.objects.filter(combo=self.cubeta, producto=self.cerveza).update(cantidad=10)
        anular_venta(venta, usuario=self.admin, motivo='Error')
        self.recargar(self.cerveza, self.hielo)
        self.assertEqual((self.cerveza.stock, self.hielo.stock), (12, 50))

    def test_respuesta_de_cobro_trae_stock_del_combo(self):
        self.client.force_login(self.cajero)
        r = self.client.post(reverse('ventas:cobrar'), json.dumps({
            'metodo': 'Efectivo', 'recibido': 2000, 'lineas': [{'id': self.cubeta.pk, 'cantidad': 1}]}),
            content_type='application/json')
        self.assertEqual(r.status_code, 200, r.content)
        stock = r.json()['stock']
        self.assertEqual(stock, {str(self.cerveza.pk): 7, str(self.hielo.pk): 49, str(self.cubeta.pk): 1})

    def test_costo_del_combo_sigue_al_de_sus_productos(self):
        registrar_entrada(producto_id=self.cerveza.pk, cantidad=24, costo=120, usuario=self.admin)
        self.recargar(self.cubeta)
        self.assertEqual(self.cubeta.costo, 620)  # 5 × 120 + 20

    # ---------- mesas ----------
    def test_mesas_apartan_los_productos_del_combo(self):
        ana = Mesera.objects.create(nombre='Ana')
        m1, m2 = Mesa.objects.get(nombre='Mesa 1'), Mesa.objects.get(nombre='Mesa 2')
        self.client.force_login(self.cajero)

        def post(ruta, mesa, **datos):
            return self.client.post(reverse(f'mesas:{ruta}', args=[mesa.pk]), json.dumps(datos), content_type='application/json')

        post('abrir', m1, mesera=ana.pk)
        post('abrir', m2, mesera=ana.pk)
        self.assertTrue(post('consumo', m1, producto=self.cubeta.pk, delta=1).json()['ok'])
        self.assertTrue(post('consumo', m2, producto=self.cerveza.pk, delta=4).json()['ok'])
        r = post('consumo', m2, producto=self.cubeta.pk, delta=1)
        self.assertEqual(r.status_code, 400)
        self.assertIn('No alcanza Presidente para otro Cubeta 5 Presidente', r.json()['error'])
        r = post('cobrar', m1, metodo='Efectivo', recibido=2000)
        self.assertTrue(r.json()['ok'], r.json())
        self.recargar(self.cerveza)
        self.assertEqual(self.cerveza.stock, 7)

    # ---------- formulario ----------
    def datos(self, **extra):
        d = {'nombre': 'Combo Brugal', 'categoria': self.beb.pk, 'precio': '1500', 'costo': '', 'stock_minimo': '0',
             'es_combo': 'on', 'activo': 'on',
             'comp-TOTAL_FORMS': '2', 'comp-INITIAL_FORMS': '0', 'comp-MIN_NUM_FORMS': '0', 'comp-MAX_NUM_FORMS': '1000',
             'comp-0-producto': self.cerveza.pk, 'comp-0-cantidad': '2',
             'comp-1-producto': self.hielo.pk, 'comp-1-cantidad': '1'}
        d.update(extra)
        return d

    def test_crear_combo_desde_la_pantalla(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('productos:nuevo'), self.datos(stock_inicial='30', controla_stock='on'))
        self.assertEqual(r.status_code, 302, r.content.decode()[:3000])
        combo = Producto.objects.get(nombre='Combo Brugal')
        self.assertTrue(combo.es_combo)
        self.assertEqual((combo.stock, combo.controla_stock, combo.costo), (0, False, 240))
        self.assertEqual(list(combo.componentes.values_list('producto__nombre', 'cantidad')), [('Presidente', 2), ('Hielo', 1)])
        self.assertFalse(Movimiento.objects.filter(producto=combo).exists())

    def test_editar_combo_cambia_sus_productos(self):
        self.client.force_login(self.admin)
        items = list(self.cubeta.componentes.all())
        r = self.client.post(reverse('productos:editar', args=[self.cubeta.pk]), self.datos(**{
            'nombre': 'Cubeta 5 Presidente', 'precio': '950', 'comp-TOTAL_FORMS': '2', 'comp-INITIAL_FORMS': '2',
            'comp-0-id': items[0].pk, 'comp-0-producto': self.cerveza.pk, 'comp-0-cantidad': '6',
            'comp-1-id': items[1].pk, 'comp-1-producto': self.hielo.pk, 'comp-1-cantidad': '1', 'comp-1-DELETE': 'on'}))
        self.assertEqual(r.status_code, 302, r.content.decode()[:3000])
        self.recargar(self.cubeta)
        self.assertEqual(list(self.cubeta.componentes.values_list('producto_id', 'cantidad')), [(self.cerveza.pk, 6)])
        self.assertEqual((self.cubeta.precio, self.cubeta.costo), (950, 660))

    def test_errores_del_formulario_de_combo(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('productos:nuevo'), self.datos(**{'comp-1-producto': self.cerveza.pk}))
        self.assertContains(r, 'Un producto está repetido', status_code=400)
        r = self.client.post(reverse('productos:nuevo'), self.datos(**{'comp-TOTAL_FORMS': '0'}))
        self.assertContains(r, 'Agrega al menos un producto', status_code=400)
        r = self.client.post(reverse('productos:nuevo'), self.datos(**{'comp-0-producto': self.cubeta.pk}))
        self.assertContains(r, 'Revisa los productos del combo', status_code=400)
        # un producto con stock no se convierte en combo
        r = self.client.post(reverse('productos:editar', args=[self.hielo.pk]), self.datos(nombre='Hielo'))
        self.assertContains(r, 'tiene 50 en inventario', status_code=400)

    def test_pantallas_muestran_el_combo(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('productos:inicio'))
        self.assertContains(r, '<span class="badge">Combo</span>', html=True)
        r = self.client.get(reverse('venta_directa:inicio'))
        self.assertContains(r, f'data-id="{self.cubeta.pk}"')
        self.assertContains(r, 'data-stock="2"')
        r = self.client.get(reverse('productos:editar', args=[self.cubeta.pk]))
        self.assertContains(r, 'id="comboCaja"')
        self.assertContains(r, 'comp-TOTAL_FORMS')
