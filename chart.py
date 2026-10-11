"""Gewichtsverlauf als Inline-SVG (keine Bibliothek): Tageswerte als Punkte, Wochen-Ø als Linie."""
from datetime import date, timedelta

from markupsafe import Markup

B, H = 600, 240
RAND_L, RAND_R, RAND_O, RAND_U = 44, 12, 12, 28


def gewichtsverlauf_svg(eintraege, wochen, start):
    punkte = [(date.fromisoformat(e["datum"]), e["gewicht"])
              for e in eintraege if e["gewicht"] is not None]
    if len(punkte) < 2:
        return Markup("")
    # Wochen-Ø wird in der Wochenmitte (Donnerstag) eingezeichnet
    mittel = [(z["von"] + timedelta(days=3), z["gewicht_avg"])
              for z in wochen if z["gewicht_avg"] is not None]

    d0, d1 = min(d for d, _ in punkte), max(d for d, _ in punkte)
    spanne_tage = max((d1 - d0).days, 1)
    werte = [w for _, w in punkte]
    lo, hi = min(werte), max(werte)
    pad = max((hi - lo) * 0.15, 0.5)
    lo, hi = lo - pad, hi + pad

    def x(d):
        return RAND_L + (d - d0).days / spanne_tage * (B - RAND_L - RAND_R)

    def y(w):
        return RAND_O + (hi - w) / (hi - lo) * (H - RAND_O - RAND_U)

    teile = [f'<svg viewBox="0 0 {B} {H}" role="img" aria-label="Gewichtsverlauf" '
             f'style="width:100%;height:auto">']
    for i in range(5):  # Hilfslinien + Beschriftung der y-Achse
        w = lo + (hi - lo) * i / 4
        teile.append(f'<line x1="{RAND_L}" x2="{B - RAND_R}" y1="{y(w):.1f}" y2="{y(w):.1f}" '
                     f'stroke="#313846"/>'
                     f'<text x="{RAND_L - 6}" y="{y(w) + 4:.1f}" text-anchor="end" '
                     f'font-size="11" fill="#8b93a1">{f"{w:.1f}".replace(".", ",")}</text>')
    # x-Achse: ein Label pro Montag (Wochenbeginn), bei langem Verlauf ausgedünnt
    montage = [z["von"] for z in wochen if d0 <= z["von"] <= d1]
    schritt = max(1, len(montage) // 6 + (1 if len(montage) % 6 else 0))
    for m in montage[::schritt]:
        teile.append(f'<text x="{x(m):.1f}" y="{H - 8}" text-anchor="middle" font-size="11" '
                     f'fill="#8b93a1">{m.strftime("%d.%m.")}</text>')
    if len(mittel) >= 2:
        pfad = " ".join(f"{x(d):.1f},{y(w):.1f}" for d, w in mittel)
        teile.append(f'<polyline points="{pfad}" fill="none" stroke="#2ecc71" stroke-width="2.5"/>')
    for d, w in punkte:
        teile.append(f'<circle cx="{x(d):.1f}" cy="{y(w):.1f}" r="3.5" fill="#8b93a1">'
                     f'<title>{d.strftime("%d.%m.")}: {w:.1f} kg</title></circle>')
    for d, w in mittel:
        teile.append(f'<circle cx="{x(d):.1f}" cy="{y(w):.1f}" r="4.5" fill="#2ecc71">'
                     f'<title>Ø Woche: {w:.2f} kg</title></circle>')
    teile.append("</svg>")
    return Markup("".join(teile))
