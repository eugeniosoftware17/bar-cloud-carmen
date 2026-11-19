/* Bar Cloud · Mesas: elegir mesa, abrir cuenta, agregar consumos, pre-cuenta, cobrar y liberar.
   El servidor guarda todo y devuelve la rejilla y la cuenta ya pintadas. */
(function () {
  'use strict';
  const { $, $$, aviso, modal, confirmar, imprimirUrl, post } = window.Caja;
  const CFG = $('#config').dataset;
  const base = CFG.base;
  let sel = CFG.sel ? +CFG.sel : null;
  let enCuenta = JSON.parse(CFG.enCuenta || '{}');
  let metodo = 'Efectivo';
  let picker = null;
  const movil = () => window.matchMedia('(max-width:900px)').matches;

  function pintar(res) {
    if (res.grid !== undefined) $('#grid').innerHTML = res.grid;
    if (res.cuenta !== undefined) $('#cuenta').innerHTML = res.cuenta;
    if (res.libres !== undefined) { $('#nLibres').textContent = res.libres; $('#nOcupadas').textContent = res.ocupadas; }
    if (res.en_cuenta) enCuenta = res.en_cuenta;
    // conservar el método de pago elegido
    $$('#cuenta [data-metodo]').forEach(b => b.classList.toggle('activo', b.dataset.metodo === metodo));
    if (picker) pintarPicker();
  }

  function url(accion) { return base + sel + '/' + accion + '/'; }

  function accion(nombre, datos) {
    return post(url(nombre), datos, CFG.csrf).then(res => {
      pintar(res);
      if (!res.ok) aviso(res.error || 'No se pudo completar.');
      return res;
    });
  }

  function elegir(id) {
    sel = id;
    history.replaceState(null, '', base + '?mesa=' + id);
    fetch(CFG.estado + '?mesa=' + id).then(r => r.json()).then(pintar).then(() => panel(true));
  }

  function panel(v) {
    const c = $('#cuenta'), f = $('#fondoPanel');
    if (v && !movil()) return;
    c.classList.toggle('abierta', v); f.classList.toggle('ver', v);
    document.body.classList.toggle('sin-scroll', v);
  }

  /* ---------- ventana "Agregar consumo" ---------- */
  let pkCat = null, pkQ = '';
  function abrirPicker() {
    const nombre = ($('#cuenta .cuenta-cab h2') || {}).firstChild;
    picker = modal({
      titulo: 'Agregar consumo' + (nombre ? ' · ' + nombre.textContent.replace(' · ', '').trim() : ''),
      ancho: 'grande', ok: 'Listo', sinOk: false, cancelar: 'Cerrar',
      html: $('#plantillaPicker').innerHTML,
      onAbrir(m) {
        const act = $('.pestana.activo', m);
        pkCat = act ? act.dataset.cat : null; pkQ = '';
        $('#pkTabs', m).onclick = e => {
          const b = e.target.closest('.pestana'); if (!b) return;
          pkCat = b.dataset.cat; pkQ = ''; $('#pkQ', m).value = '';
          $$('.pestana', m).forEach(x => x.classList.toggle('activo', x === b)); pintarPicker();
        };
        $('#pkQ', m).oninput = e => { pkQ = e.target.value.trim().toLowerCase(); pintarPicker(); };
        $('#pkGrid', m).onclick = e => {
          const b = e.target.closest('.tarjeta'); if (!b || b.classList.contains('agotado')) return;
          accion('consumo', { producto: +b.dataset.id, delta: 1 });
        };
        setTimeout(() => $('#pkQ', m).focus(), 40);
      },
      onOk(m) { m.cerrar(); },
      onCerrar() { picker = null; }
    });
    pintarPicker();
  }

  function pintarPicker() {
    if (!picker) return;
    let visibles = 0;
    $$('#pkGrid .tarjeta', picker).forEach(t => {
      const ver = pkQ ? t.dataset.nombre.includes(pkQ) : t.dataset.cat === pkCat;
      t.hidden = !ver; if (ver) visibles++;
      const n = enCuenta[t.dataset.id] || 0, c = $('.cuantos', t);
      c.hidden = !n; c.textContent = n;
    });
    $('#pkVacio', picker).hidden = visibles > 0;
  }

  /* ---------- eventos ---------- */
  $('#grid').addEventListener('click', e => { const b = e.target.closest('.mesa'); if (b) elegir(+b.dataset.id); });

  $('#cuenta').addEventListener('click', e => {
    const mas = e.target.closest('[data-mas]'), menos = e.target.closest('[data-menos]');
    if (mas) return accion('consumo', { producto: +mas.dataset.mas, delta: 1 });
    if (menos) return accion('consumo', { producto: +menos.dataset.menos, delta: -1 });
    const met = e.target.closest('[data-metodo]');
    if (met) { metodo = met.dataset.metodo; $$('#cuenta [data-metodo]').forEach(b => b.classList.toggle('activo', b === met)); return; }
    const b = e.target.closest('[data-accion]'); if (!b) return;
    switch (b.dataset.accion) {
      case 'abrir': accion('abrir').then(r => { if (r.ok) abrirPicker(); }); break;
      case 'agregar': abrirPicker(); break;
      case 'cerrar-panel': panel(false); break;
      case 'precuenta': imprimirUrl(url('precuenta') + '?imprimir=1'); break;
      case 'liberar': {
        const hacer = () => accion('liberar').then(r => { if (r.ok) { panel(false); aviso('Mesa liberada'); } });
        if (+b.dataset.conConsumos) confirmar('Liberar mesa', 'Se descartan los consumos de esta mesa sin cobrarlos. ¿Continuar?', 'Liberar', hacer);
        else hacer();
        break;
      }
      case 'cobrar':
        Caja.cobrar({
          titulo: 'Cobrar ' + $('#cuenta .cuenta-cab h2').firstChild.textContent.replace(' · ', '').trim(),
          total: +b.dataset.total, metodo, url: url('cobrar'), csrf: CFG.csrf,
          onListo(res) { pintar(res); panel(false); }
        });
        break;
    }
  });

  const bm = $('#btnMesa');
  if (bm) bm.addEventListener('click', () => {
    post(CFG.nueva, {}, CFG.csrf).then(res => {
      if (!res.ok) { aviso(res.error); return; }
      pintar(res); aviso(res.nombre + ' agregada');
    });
  });

  $('#fondoPanel').addEventListener('click', () => panel(false));
  window.addEventListener('resize', () => { if (!movil()) panel(false); });

  // mantener al día lo que hacen otras cajas (y el tiempo de cada mesa)
  setInterval(() => {
    if (document.hidden || $('.velo')) return;
    fetch(CFG.estado + (sel ? '?mesa=' + sel : '')).then(r => r.json()).then(pintar).catch(() => {});
  }, 30000);
})();
