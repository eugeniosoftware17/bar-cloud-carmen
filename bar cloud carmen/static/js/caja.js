/* Bar Cloud · piezas comunes de caja: avisos, ventanas, impresión y cobro.
   Lo usan Venta directa y Mesas. */
(function (w) {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s), $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const money = n => 'RD$ ' + Math.round(n || 0).toLocaleString('en-US');
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  let tAviso;
  function aviso(txt) {
    let a = $('#aviso');
    if (!a) { a = document.createElement('div'); a.id = 'aviso'; a.className = 'aviso'; a.setAttribute('role', 'status'); document.body.appendChild(a); }
    a.textContent = txt; a.classList.add('ver'); clearTimeout(tAviso); tAviso = setTimeout(() => a.classList.remove('ver'), 3000);
  }

  /* Ventana con el estilo del diseño. o: {titulo, html, ok, cancelar, ancho, sinOk, onAbrir, onOk, onCancelar, onCerrar} */
  function modal(o) {
    const velo = document.createElement('div'); velo.className = 'velo';
    velo.innerHTML = '<div class="modal' + (o.ancho ? ' ' + o.ancho : '') + '" role="dialog" aria-modal="true" aria-label="' + esc(o.titulo) + '"><h2>' + esc(o.titulo) + '</h2><div class="cuerpo">' + o.html + '</div>' +
      '<div class="acciones fila2"><button type="button" class="btn sec" data-x="cancel">' + (o.cancelar || 'Cancelar') + '</button>' +
      (o.sinOk ? '' : '<button type="button" class="btn prim" data-x="ok">' + (o.ok || 'Aceptar') + '</button>') + '</div></div>';
    document.body.appendChild(velo);
    const m = velo.firstChild;
    let cerrado = false;
    const cerrar = () => { if (cerrado) return; cerrado = true; velo.remove(); document.removeEventListener('keydown', tecla); if (o.onCerrar) o.onCerrar(); };
    const tecla = e => { if (e.key === 'Escape' && !m.dataset.ocupado) cerrar(); };
    document.addEventListener('keydown', tecla);
    velo.addEventListener('mousedown', e => { if (e.target === velo && !m.dataset.ocupado) cerrar(); });
    m.cerrar = cerrar;
    $('[data-x=cancel]', m).onclick = () => { if (o.onCancelar && o.onCancelar(m) === false) return; cerrar(); };
    const ok = $('[data-x=ok]', m); if (ok) ok.onclick = () => { if (o.onOk) o.onOk(m); };
    if (o.onAbrir) o.onAbrir(m);
    return m;
  }

  function confirmar(titulo, texto, etiqueta, fn) {
    return modal({ titulo, html: '<p class="mmetodo">' + esc(texto) + '</p>', ok: etiqueta || 'Confirmar', onOk(m) { m.cerrar(); fn(); } });
  }

  /* imprime una página (recibo, pre-cuenta…) sin salir de la pantalla */
  function imprimirUrl(url) {
    let f = $('#marcoRecibo'); if (f) f.remove();
    f = document.createElement('iframe'); f.id = 'marcoRecibo'; f.title = 'Impresión';
    f.style.cssText = 'position:fixed;width:0;height:0;border:0;right:0;bottom:0';
    f.src = url; document.body.appendChild(f);
  }

  function post(url, datos, csrf) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(datos || {})
    }).then(r => r.json().catch(() => ({ ok: false, error: 'Respuesta inválida del servidor.' })))
      .catch(() => ({ ok: false, error: 'Sin conexión con el servidor. Intenta de nuevo.' }));
  }

  /* Ventana de cobro. o: {titulo, total, metodo, url, csrf, datos(): {}, onListo(res)} */
  function cobrar(o) {
    let met = o.metodo || 'Efectivo';
    const total = o.total;
    modal({
      titulo: o.titulo || 'Cobrar venta', ok: 'Confirmar cobro',
      html: '<p class="mtotal">' + money(total) + '</p>' +
        '<div class="metodos" id="cbMetodos">' + ['Efectivo', 'Tarjeta', 'Transferencia'].map(x => '<button type="button" class="metodo' + (x === met ? ' activo' : '') + '" data-m="' + x + '">' + x + '</button>').join('') + '</div>' +
        '<div id="cbEf"><label for="cbRec">Monto recibido</label><input id="cbRec" type="number" min="0" step="1" inputmode="numeric" placeholder="0"><div class="rapidos" id="cbRap"></div><p class="cambio">Cambio: <b id="cbCambio">RD$ 0</b></p></div>' +
        '<div id="cbRef" hidden><label for="cbRefIn">Referencia (opcional)</label><input id="cbRefIn" type="text" maxlength="60" placeholder="Últimos 4 dígitos o nº de transferencia"></div>' +
        '<p class="campo-error" id="cbError" hidden></p>',
      onAbrir(m) {
        const rec = $('#cbRec', m), ok = $('[data-x=ok]', m);
        const rap = [total, 500, 1000, 2000, 5000].filter((v, i, a) => v >= total && a.indexOf(v) === i).slice(0, 4);
        $('#cbRap', m).innerHTML = rap.map((v, i) => '<button type="button" data-v="' + v + '">' + (i === 0 ? 'Exacto' : money(v)) + '</button>').join('');
        const act = () => {
          const ef = met === 'Efectivo', r = parseFloat(rec.value) || 0;
          $('#cbEf', m).hidden = !ef; $('#cbRef', m).hidden = ef;
          $('#cbCambio', m).textContent = money(Math.max(0, r - total));
          ok.disabled = ef && r < total;
        };
        $('#cbMetodos', m).onclick = e => {
          const b = e.target.closest('.metodo'); if (!b) return;
          met = b.dataset.m; $$('.metodo', m).forEach(x => x.classList.toggle('activo', x === b)); act();
          setTimeout(() => (met === 'Efectivo' ? rec : $('#cbRefIn', m)).focus(), 20);
        };
        $('#cbRap', m).onclick = e => { const b = e.target.closest('button'); if (b) { rec.value = b.dataset.v; act(); rec.focus(); } };
        rec.oninput = act; act();
        m.addEventListener('keydown', e => { if (e.key === 'Enter' && !ok.disabled) { e.preventDefault(); ok.click(); } });
        setTimeout(() => (met === 'Efectivo' ? rec : $('#cbRefIn', m)).focus(), 40);
      },
      onOk(m) {
        const ok = $('[data-x=ok]', m), err = $('#cbError', m);
        if (ok.disabled) return;
        ok.disabled = true; ok.textContent = 'Guardando…'; m.dataset.ocupado = '1'; err.hidden = true;
        const datos = Object.assign({}, o.datos ? o.datos() : {}, {
          metodo: met,
          recibido: met === 'Efectivo' ? parseFloat($('#cbRec', m).value) || 0 : null,
          referencia: met === 'Efectivo' ? '' : $('#cbRefIn', m).value.trim()
        });
        post(o.url, datos, o.csrf).then(res => {
          if (!res.ok) {
            delete m.dataset.ocupado; ok.disabled = false; ok.textContent = 'Confirmar cobro';
            err.textContent = res.error || 'No se pudo cobrar.'; err.hidden = false;
            return;
          }
          delete m.dataset.ocupado; m.cerrar();
          if (o.onListo) o.onListo(res);
          listo(res);
        });
      }
    });
  }

  function listo(res) {
    const v = res.venta, ef = v.metodo === 'Efectivo';
    // Configuración → "Imprimir al cobrar": el recibo sale solo (sin ventana si la caja usa el acceso "Bar Cloud - Caja")
    if (res.imprimir_auto) imprimirUrl(res.recibo + '?imprimir=1');
    modal({
      titulo: 'Venta #' + v.numero + ' registrada', ok: 'Listo', cancelar: res.imprimir_auto ? 'Imprimir otra vez' : 'Imprimir recibo', ancho: 'chico',
      html: '<p class="mtotal">' + money(v.total) + '</p><p class="mmetodo fuerte">' + (ef ? 'Cambio a devolver: <b>' + money(v.cambio) + '</b>' : 'Pagado con ' + v.metodo.toLowerCase()) + '</p>' +
        (res.alertas && res.alertas.length ? '<p class="alerta">Queda poco: ' + res.alertas.map(esc).join(', ') + '</p>' : ''),
      onAbrir(m) { setTimeout(() => $('[data-x=ok]', m).focus(), 40); },
      onCancelar() { imprimirUrl(res.recibo + '?imprimir=1'); return false; },
      onOk(m) { m.cerrar(); }
    });
  }

  w.Caja = { $, $$, money, esc, aviso, modal, confirmar, imprimirUrl, post, cobrar };
})(window);
