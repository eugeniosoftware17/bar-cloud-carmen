/* Bar Cloud · Mesas: elegir mesa, abrir cuenta, agregar consumos, pre-cuenta, cobrar y liberar.
   El servidor guarda todo y devuelve la rejilla y la cuenta ya pintadas. */
(function () {
  'use strict';
  const { $, $$, aviso, modal, confirmar, imprimirUrl, post } = window.Caja;
  const esc = t => String(t == null ? '' : t).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const CFG = $('#config').dataset;
  const base = CFG.base;
  let sel = CFG.sel ? +CFG.sel : null;
  let enCuenta = JSON.parse(CFG.enCuenta || '{}');
  let meseras = JSON.parse(CFG.meseras || '[]');
  let meseraActual = CFG.meseraActual ? +CFG.meseraActual : null;
  let ventanaMesera = null;
  let metodo = 'Efectivo';
  let picker = null;
  const movil = () => window.matchMedia('(max-width:900px)').matches;

  function pintar(res) {
    if (res.grid !== undefined) $('#grid').innerHTML = res.grid;
    if (res.cuenta !== undefined) $('#cuenta').innerHTML = res.cuenta;
    if (res.libres !== undefined) { $('#nLibres').textContent = res.libres; $('#nOcupadas').textContent = res.ocupadas; }
    if (res.en_cuenta) enCuenta = res.en_cuenta;
    if (res.meseras) { meseras = res.meseras; if (ventanaMesera) ventanaMesera.pintar(); }
    if (res.mesera !== undefined) meseraActual = res.mesera;
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

  function nombreMesa() {
    const h = $('#cuenta .cuenta-cab h2');
    return h ? h.firstChild.textContent.replace(' · ', '').trim() : 'la mesa';
  }

  /* ---------- ventana "¿Quién atiende?" ----------
     Se toca un nombre de la lista o se escribe uno nuevo (queda guardado para la próxima). */
  function elegirMesera(titulo, actual, fn) {
    ventanaMesera = modal({
      titulo, ok: 'Agregar y elegir', cancelar: 'Cancelar',
      html: '<div class="lista-meseras" id="msLista"></div><p class="sub lista-meseras-vacia" id="msVacia" hidden>Todavía no hay meseras en la lista. Escribe el nombre de quien atiende.</p>' +
        '<label for="msNombre">Otra persona</label><input id="msNombre" type="text" maxlength="40" autocomplete="off" placeholder="Nombre de la mesera">' +
        '<p class="campo-error" id="msError" hidden></p>',
      onAbrir(m) {
        const inp = $('#msNombre', m), ok = $('[data-x=ok]', m);
        m.pintar = () => {
          $('#msLista', m).innerHTML = meseras.map(x =>
            '<div class="mesera' + (x.id === actual ? ' activo' : '') + '" role="button" tabindex="0" data-id="' + x.id + '">' + esc(x.nombre) +
            '<button type="button" class="quitar" data-quitar="' + x.id + '" title="Quitar de la lista" aria-label="Quitar a ' + esc(x.nombre) + ' de la lista">×</button></div>').join('');
          $('#msVacia', m).hidden = meseras.length > 0;
          $('#msLista', m).hidden = !meseras.length;
        };
        m.pintar();
        const act = () => { ok.disabled = !inp.value.trim(); };
        inp.oninput = act; act();
        inp.onkeydown = e => { if (e.key === 'Enter' && inp.value.trim()) ok.click(); };
        const elegir = el => { m.cerrar(); fn({ mesera: +el.dataset.id }); };
        $('#msLista', m).onclick = e => {
          const q = e.target.closest('[data-quitar]');
          if (q) {
            e.stopPropagation();
            const x = meseras.find(y => y.id === +q.dataset.quitar);
            post(CFG.quitarMesera.replace('/0/', '/' + q.dataset.quitar + '/') + (sel ? '?mesa=' + sel : ''), {}, CFG.csrf).then(res => {
              if (res.ok) { pintar(res); aviso((x ? x.nombre : 'Mesera') + ' quitada de la lista'); } else aviso(res.error || 'No se pudo quitar.');
            });
            return;
          }
          const b = e.target.closest('.mesera'); if (b) elegir(b);
        };
        $('#msLista', m).onkeydown = e => { const b = e.target.closest('.mesera'); if (b && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); elegir(b); } };
        if (!meseras.length) setTimeout(() => inp.focus(), 40);
      },
      onOk(m) { const n = $('#msNombre', m).value.trim(); if (!n) return; m.cerrar(); fn({ nombre: n }); },
      onCerrar() { ventanaMesera = null; }
    });
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
      case 'abrir':
        elegirMesera('¿Quién atiende ' + nombreMesa() + '?', null, datos =>
          accion('abrir', datos).then(r => { if (r.ok) abrirPicker(); }));
        break;
      case 'mesera':
        elegirMesera('¿Quién atiende ' + nombreMesa() + '?', meseraActual, datos =>
          accion('mesera', datos).then(r => { if (r.ok) aviso('Ahora atiende ' + (($('#cuenta .atiende-fila b') || {}).textContent || '')); }));
        break;
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
