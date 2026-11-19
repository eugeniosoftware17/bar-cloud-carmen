/* Bar Cloud · comportamiento común: modo claro/oscuro, menú del usuario, menú en celular, avisos */
(function () {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* sin almacenamiento */ } };

  // Modo claro / oscuro
  function aplicarTema(t) {
    document.documentElement.dataset.tema = t;
    const b = $('#btnTema');
    if (b) b.setAttribute('aria-checked', String(t === 'oscuro'));
    guardar('barcloud_tema', t);
  }
  aplicarTema(document.documentElement.dataset.tema || 'claro');
  const bt = $('#btnTema');
  if (bt) bt.addEventListener('click', () => aplicarTema(document.documentElement.dataset.tema === 'oscuro' ? 'claro' : 'oscuro'));

  // Menú del usuario (cerrar sesión)
  const bu = $('#btnUsuario'), pop = $('#popUsuario');
  if (bu && pop) {
    const mostrar = v => { pop.hidden = !v; bu.setAttribute('aria-expanded', String(v)); };
    bu.addEventListener('click', e => { if (!e.target.closest('#popUsuario')) mostrar(pop.hidden); });
    bu.addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && e.target === bu) { e.preventDefault(); mostrar(pop.hidden); } });
    document.addEventListener('click', e => { if (!e.target.closest('#btnUsuario')) mostrar(false); });
  }

  // Menú deslizable (celular y tablet vertical)
  const lat = $('#lateral'), fm = $('#fondoMenu'), bm = $('#btnMenu');
  function menu(v) {
    if (!lat) return;
    lat.classList.toggle('abierto', v);
    if (fm) fm.classList.toggle('ver', v);
    document.body.classList.toggle('sin-scroll', v);
    if (bm) bm.setAttribute('aria-expanded', String(v));
  }
  if (bm) bm.addEventListener('click', () => menu(!lat.classList.contains('abierto')));
  if (fm) fm.addEventListener('click', () => menu(false));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') { menu(false); if (pop) pop.hidden = true; } });
  window.addEventListener('resize', () => { if (!window.matchMedia('(max-width:900px)').matches) menu(false); });

  // Fecha de la barra superior
  document.querySelectorAll('[data-fecha]').forEach(el => {
    el.textContent = new Date().toLocaleDateString('es-DO', { day: '2-digit', month: 'long', year: 'numeric' });
  });

  // Avisos de Django (messages)
  const av = $('#aviso');
  if (av) { requestAnimationFrame(() => av.classList.add('ver')); setTimeout(() => av.classList.remove('ver'), 3200); }

  // Ctrl + K o "/" enfocan el buscador de la página
  document.addEventListener('keydown', e => {
    const q = $('[data-buscador]');
    if (!q) return;
    const enCampo = /INPUT|TEXTAREA|SELECT/.test((document.activeElement || {}).tagName || '');
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); q.focus(); q.select(); }
    else if (e.key === '/' && !enCampo) { e.preventDefault(); q.focus(); }
  });
})();
