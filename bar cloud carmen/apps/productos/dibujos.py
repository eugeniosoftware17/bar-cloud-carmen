"""Dibujos SVG de los productos (los mismos del diseño Nuevo). Se usan cuando el producto no tiene foto."""

from django.utils.html import escape

_V = '<svg viewBox="0 0 60 90" aria-hidden="true">'

_DIBUJOS = {
    'cerveza': '<rect x="25" y="2" width="10" height="5" rx="1.5" fill="#b8892b"/><path d="M25 6h10v6l-1 2v16l7 12v38a5 5 0 0 1-5 5H24a5 5 0 0 1-5-5V42l7-12V14l-1-2z" fill="#2f6b3a"/><rect x="21" y="48" width="18" height="24" rx="2" fill="#f2ead3"/><circle cx="30" cy="60" r="4.5" fill="#2f6b3a"/>',
    'ron': '<rect x="24" y="3" width="12" height="7" rx="2" fill="#c9a24a"/><path d="M26 10h8v14l7 10v46a5 5 0 0 1-5 5H24a5 5 0 0 1-5-5V34l7-10z" fill="{c}"/><rect x="21" y="44" width="18" height="26" rx="2" fill="#f2ead3"/><rect x="24" y="50" width="12" height="3" fill="{c}"/><rect x="24" y="57" width="12" height="3" fill="#c9a24a"/>',
    'refresco': '<rect x="24" y="2" width="12" height="7" rx="2" fill="#c4262e"/><path d="M26 9h8v10c0 6 8 10 8 20v38a6 6 0 0 1-6 6H24a6 6 0 0 1-6-6V39c0-10 8-14 8-20z" fill="#2a1612"/><rect x="18" y="44" width="24" height="22" fill="#c4262e"/><rect x="22" y="52" width="16" height="4" rx="2" fill="#fff"/>',
    'agua': '<rect x="24" y="2" width="12" height="7" rx="2" fill="#8d949b"/><path d="M26 9h8v10c0 6 8 10 8 20v38a6 6 0 0 1-6 6H24a6 6 0 0 1-6-6V39c0-10 8-14 8-20z" fill="#d6dbde"/><path d="M22 40h16v34H22z" fill="#eef1f3"/><rect x="18" y="50" width="24" height="10" fill="#9aa1a8"/>',
    'jugo': '<path d="M12 22h36l-4 62H16z" fill="#e5e5e4"/><path d="M14.5 32h31l-3 50H17.5z" fill="#f59e0b"/><ellipse cx="30" cy="22" rx="18" ry="3.5" fill="#d6d3d1"/><circle cx="46" cy="22" r="8" fill="#fbbf24"/>',
    'pina': '<path d="M20 8l4 10 6-12 4 12 6-8 0 10H20z" fill="#3f8f4a"/><path d="M12 24h36c0 16-10 26-18 28-8-2-18-12-18-28z" fill="#f5ecd7"/><path d="M14 24h32" stroke="#e7dcc0" stroke-width="3"/><rect x="28" y="52" width="4" height="24" fill="#d6d3d1"/><ellipse cx="30" cy="78" rx="14" ry="3.5" fill="#d6d3d1"/><path d="M38 14l12-10v12z" fill="#facc15"/>',
    'mojito': '<circle cx="22" cy="12" r="6" fill="#3f8f4a"/><circle cx="32" cy="9" r="6" fill="#57a85f"/><circle cx="40" cy="14" r="5" fill="#3f8f4a"/><path d="M14 16h32l-3 66H17z" fill="#e8f2e4"/><rect x="20" y="30" width="10" height="10" rx="2" fill="#fff"/><rect x="31" y="42" width="10" height="10" rx="2" fill="#fff"/><rect x="20" y="54" width="10" height="10" rx="2" fill="#fff"/><circle cx="46" cy="18" r="8" fill="#a3c93a"/><circle cx="46" cy="18" r="5" fill="#d9eb8a"/>',
    'burger': '<path d="M8 36c0-14 10-22 22-22s22 8 22 22z" fill="#d79a46"/><rect x="8" y="38" width="44" height="6" rx="3" fill="#57a85f"/><rect x="8" y="46" width="44" height="10" rx="5" fill="#5a3320"/><rect x="8" y="58" width="44" height="5" rx="2.5" fill="#f2c94c"/><path d="M8 65h44c0 8-6 12-12 12H20c-6 0-12-4-12-12z" fill="#d79a46"/>',
    'pollo': '<path d="M16 34c0-14 10-22 22-18s12 16 4 26c-6 8-14 10-20 6l-10 14-6-6 10-14c-2-3-2-5 0-8z" fill="#c97a2b"/><rect x="2" y="64" width="14" height="6" rx="3" transform="rotate(-40 9 67)" fill="#f2ead3"/>',
    'tostones': '<ellipse cx="30" cy="62" rx="26" ry="9" fill="#e7e5e4"/><ellipse cx="20" cy="54" rx="11" ry="8" fill="#e0b341"/><ellipse cx="38" cy="52" rx="11" ry="8" fill="#ebc356"/><ellipse cx="30" cy="42" rx="11" ry="8" fill="#e0b341"/>',
    'sandwich': '<path d="M6 48L30 22l24 26z" fill="#e8c27a"/><path d="M10 52L30 30l20 22z" fill="#57a85f"/><path d="M12 56L30 38l18 18z" fill="#f2c94c"/><rect x="6" y="58" width="48" height="10" rx="4" fill="#d79a46"/>',
    'bolsa': '<path d="M12 10h36l-3 70H15z" fill="{c}"/><path d="M12 10h36v6l-4 2-4-2-4 2-4-2-4 2-4-2-4 2-4-2z" fill="#18181b" opacity=".25"/><circle cx="30" cy="46" r="12" fill="#fff" opacity=".85"/><path d="M24 46h12" stroke="{c}" stroke-width="3"/>',
    'hielo': '<rect x="8" y="44" width="26" height="26" rx="4" fill="#eceff1"/><rect x="28" y="28" width="26" height="26" rx="4" fill="#fff" opacity=".95"/><rect x="26" y="56" width="24" height="22" rx="4" fill="#dfe3e6"/>',
    'vaso': '<path d="M12 18h36l-5 62H17z" fill="#e5e5e4"/><path d="M14 24h32l-4 50H18z" fill="#fff" opacity=".8"/>',
    'caja': '<rect x="12" y="28" width="36" height="42" rx="4" fill="{c}"/><rect x="12" y="28" width="36" height="12" fill="#18181b" opacity=".2"/>',
}


def svg(dibujo, color='#7a3b12'):
    cuerpo = _DIBUJOS.get(dibujo, _DIBUJOS['caja'])
    return _V + cuerpo.replace('{c}', escape(color or '#7a3b12')) + '</svg>'
