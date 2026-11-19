/* Bar Cloud · Venta directa: pestañas, búsqueda, cuenta en pantalla, cobro y pre-cuenta.
   Los totales se muestran aquí, pero el servidor los vuelve a calcular al cobrar. */
(function () {
  'use strict';
  const { $, $$, money, esc, aviso } = window.Caja;
  const CFG = $('#config').dataset;
  const PROPINA = parseFloat(CFG.propina), ITBIS = parseFloat(CFG.itbis);
  const tarjetas = $$('.tarjeta[data-id]');
  if (!tarjetas.length) return;

  const prod = {};
  tarjetas.forEach(t => {
    prod[t.dataset.id] = { id: t.dataset.id, cat: t.dataset.cat, n: t.dataset.nombre, p: +t.dataset.precio, stock: +t.dataset.stock, img: t.querySelector('.img').innerHTML, el: t };
  });
  let cat = $('.pestana.activo') ? $('.pestana.activo').dataset.cat : null;
  let carrito = {}, metodo = 'Efectivo';
  const movil = () => window.matchMedia('(max-width:900px)').matches;

  function totales() {
    const sub = Object.keys(carrito).reduce((s, id) => s + prod[id].p * carrito[id], 0);
    const prop = Math.round(sub * PROPINA), itbis = Math.round(sub * ITBIS);
    return { sub, prop, itbis, total: sub + prop + itbis };
  }

  function filtrar() {
    const q = $('#buscar').value.trim().toLowerCase();
    let visibles = 0;
    tarjetas.forEach(t => {
      const p = prod[t.dataset.id];
      const ver = q ? p.n.toLowerCase().includes(q) : p.cat === cat;
      t.hidden = !ver; if (ver) visibles++;
    });
    $('#vacio').hidden = visibles > 0;
  }

  function pintarTarjeta(p) {
    const t = p.el, tag = $('.tag', t);
    const agotado = p.stock === 0, bajo = p.stock > 0 && p.stock <= +t.dataset.minimo;
    t.classList.toggle('agotado', agotado);
    t.dataset.stock = p.stock;
    if (tag) tag.remove();
    if (agotado || bajo) t.insertAdjacentHTML('beforeend', '<span class="tag">' + (agotado ? 'Agotado' : 'Quedan ' + p.stock) + '</span>');
  }

  function pintarCuenta() {
    const ids = Object.keys(carrito), t = totales();
    $('#lineas').innerHTML = ids.map(id => {
      const p = prod[id], q = carrito[id];
      return '<li class="linea"><div class="mini">' + p.img + '</div><div class="dato"><b>' + esc(p.n) + '</b><div class="cant"><button data-menos="' + id + '" aria-label="Quitar uno">−</button><span>x' + q + '</span><button data-mas="' + id + '" aria-label="Agregar uno">+</button></div></div><span class="imp">' + money(p.p * q) + '</span></li>';
    }).join('');
    $('#cuentaVacia').hidden = ids.length > 0;
    $('#tSub').textContent = money(t.sub); $('#tProp').textContent = money(t.prop);
    $('#tItbis').textContent = money(t.itbis); $('#tTotal').textContent = money(t.total);
    $('#btnImprimir').disabled = !ids.length;
    $('#btnCobrar').disabled = !ids.length || $('#btnCobrar').hasAttribute('data-solo-ver');
    const cant = ids.reduce((a, id) => a + carrito[id], 0);
    $('#barraCarrito').hidden = !cant;
    $('#bcN').textContent = cant + (cant === 1 ? ' producto' : ' productos');
    $('#bcT').textContent = money(t.total);
    if (!cant) panel(false);
  }

  function agregar(id, n) {
    const p = prod[id], actual = carrito[id] || 0;
    if (n > 0 && p.stock >= 0 && actual + n > p.stock) {
      aviso(p.stock <= 0 ? p.n + ': agotado. Registra una entrada en Inventario.' : 'Solo quedan ' + p.stock + ' de ' + p.n);
      return;
    }
    carrito[id] = actual + n;
    if (carrito[id] <= 0) delete carrito[id];
    pintarCuenta();
  }

  function panel(v) {
    const c = $('#cuenta'), f = $('#fondoPanel');
    if (v && !movil()) return;
    c.classList.toggle('abierta', v); f.classList.toggle('ver', v);
    document.body.classList.toggle('sin-scroll', v);
  }

  function imprimirPrecuenta() {
    const t = totales();
    let r = $('#recibo');
    if (!r) { r = document.createElement('div'); r.id = 'recibo'; r.setAttribute('aria-hidden', 'true'); document.body.appendChild(r); }
    const fecha = new Date().toLocaleString('es-DO', { dateStyle: 'short', timeStyle: 'short' });
    let h = '<h1>' + esc(CFG.negocio).toUpperCase() + '</h1>' + (CFG.direccion ? '<p class="c">' + esc(CFG.direccion) + '</p>' : '') + (CFG.telefono ? '<p class="c">Tel. ' + esc(CFG.telefono) + '</p>' : '') +
      '<hr><div class="f"><span>Venta directa</span><span>' + fecha + '</span></div><p class="c"><b>PRE-CUENTA (no es comprobante)</b></p><hr>';
    Object.keys(carrito).forEach(id => { h += '<div class="f"><span>' + carrito[id] + ' x ' + esc(prod[id].n) + '</span><span>' + money(prod[id].p * carrito[id]) + '</span></div>'; });
    h += '<hr><div class="f"><span>Subtotal</span><span>' + money(t.sub) + '</span></div>' + (t.prop ? '<div class="f"><span>Propina legal</span><span>' + money(t.prop) + '</span></div>' : '') + (t.itbis ? '<div class="f"><span>ITBIS</span><span>' + money(t.itbis) + '</span></div>' : '') + '<div class="f t"><span>TOTAL</span><span>' + money(t.total) + '</span></div>';
    r.innerHTML = h;
    window.print();
  }

  function cobrar() {
    if (!Object.keys(carrito).length) return;
    Caja.cobrar({
      titulo: 'Cobrar venta', total: totales().total, metodo, url: CFG.cobrar, csrf: CFG.csrf,
      datos: () => ({ lineas: Object.keys(carrito).map(id => ({ id: +id, cantidad: carrito[id] })) }),
      onListo(res) {
        Object.keys(res.stock || {}).forEach(id => { if (prod[id]) { prod[id].stock = res.stock[id]; pintarTarjeta(prod[id]); } });
        carrito = {}; panel(false); pintarCuenta();
      }
    });
  }

  $('#productos').addEventListener('click', e => { const b = e.target.closest('.tarjeta'); if (b) agregar(b.dataset.id, 1); });
  $('#lineas').addEventListener('click', e => {
    const m = e.target.closest('[data-mas]'), n = e.target.closest('[data-menos]');
    if (m) agregar(m.dataset.mas, 1); if (n) agregar(n.dataset.menos, -1);
  });
  $('#pestanas').addEventListener('click', e => {
    const b = e.target.closest('.pestana'); if (!b) return;
    cat = b.dataset.cat; $('#buscar').value = '';
    $$('.pestana').forEach(x => { x.classList.toggle('activo', x === b); x.setAttribute('aria-selected', String(x === b)); });
    filtrar();
  });
  $('#btnVaciar').addEventListener('click', () => { if (!Object.keys(carrito).length) return; carrito = {}; pintarCuenta(); aviso('Cuenta vaciada'); });
  $('#metodos').addEventListener('click', e => {
    const b = e.target.closest('.metodo'); if (!b) return;
    metodo = b.dataset.metodo; $$('#metodos .metodo').forEach(x => x.classList.toggle('activo', x === b));
  });
  $('#btnCobrar').addEventListener('click', cobrar);
  $('#btnImprimir').addEventListener('click', imprimirPrecuenta);
  $('#buscar').addEventListener('input', filtrar);
  $('#buscar').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { const p = $('.tarjeta:not([hidden]):not(.agotado)'); if (p) { agregar(p.dataset.id, 1); this.select(); } }
    if (e.key === 'Escape') { this.value = ''; filtrar(); this.blur(); }
  });
  $('#barraCarrito').addEventListener('click', () => panel(true));
  $('#cerrarPanel').addEventListener('click', () => panel(false));
  $('#fondoPanel').addEventListener('click', () => panel(false));
  window.addEventListener('resize', () => { if (!movil()) panel(false); });
  pintarCuenta();
})();
