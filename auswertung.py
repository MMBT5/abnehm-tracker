"""Wochenauswertung. Reine Berechnung ohne DB- oder Flask-Zugriff, damit Web-Ansicht
und Excel-Export dieselbe Logik nutzen. Eingabe: Zeilen mit datum/kcal/gewicht/protein/bauch
(sqlite3.Row oder dict)."""
from datetime import date, timedelta

KCAL_PRO_KG = 7700
MIN_WIEGUNGEN_TDEE = 4    # pro Woche, in beiden verglichenen Wochen
TDEE_AB_WOCHE = 3
GLEITEND_WOCHEN = 4


def tag_nr(datum, start):
    return (datum - start).days + 1


def wochen_nr(datum, start):
    """Woche 1 beginnt am START_DATE (ein Montag -> Wochen laufen Mo-So)."""
    return (datum - start).days // 7 + 1


def woche_von_bis(woche, start):
    von = start + timedelta(days=(woche - 1) * 7)
    return von, von + timedelta(days=6)


def _mittel(werte, stellen):
    return round(sum(werte) / len(werte), stellen) if werte else None


def _diff(neu, alt, stellen):
    return round(neu - alt, stellen) if neu is not None and alt is not None else None


def wochen_auswertung(eintraege, start):
    """Eine Zeile pro Woche von Woche 1 bis zur letzten Woche mit Daten (aufsteigend).
    Wochen ohne Daten bleiben als leere Zeilen drin, damit "Vorwoche" stimmt."""
    nach_woche = {}
    for e in eintraege:
        d = date.fromisoformat(e["datum"])
        if d < start:
            continue
        nach_woche.setdefault(wochen_nr(d, start), []).append((d, e))
    if not nach_woche:
        return []

    ergebnis = []
    letzter_bauch = None  # letzter bekannter Bauchumfang aus früheren Wochen
    for w in range(1, max(nach_woche) + 1):
        tage = sorted(nach_woche.get(w, []), key=lambda t: t[0])
        gewichte = [e["gewicht"] for _, e in tage if e["gewicht"] is not None]
        kcals = [e["kcal"] for _, e in tage if e["kcal"] is not None]
        proteine = [e["protein"] for _, e in tage if e["protein"] is not None]
        baeuche = [e["bauch"] for _, e in tage if e["bauch"] is not None]
        bauch = baeuche[-1] if baeuche else None
        von, bis = woche_von_bis(w, start)
        vorwoche = ergebnis[-1] if ergebnis else None

        zeile = {
            "woche": w, "von": von, "bis": bis,
            "gewicht_avg": _mittel(gewichte, 2), "n_wiegungen": len(gewichte),
            "kcal_avg": _mittel(kcals, 0), "n_kcal": len(kcals),
            "protein_avg": _mittel(proteine, 0),
            "bauch": bauch, "bauch_diff": _diff(bauch, letzter_bauch, 1),
            "gewicht_diff": None, "tdee": None, "tdee_gleitend": None,
        }
        if vorwoche:
            zeile["gewicht_diff"] = _diff(zeile["gewicht_avg"], vorwoche["gewicht_avg"], 2)
            if (w >= TDEE_AB_WOCHE
                    and zeile["n_wiegungen"] >= MIN_WIEGUNGEN_TDEE
                    and vorwoche["n_wiegungen"] >= MIN_WIEGUNGEN_TDEE
                    and zeile["kcal_avg"] is not None
                    and zeile["gewicht_diff"] is not None):
                # Δ Gewicht ist kg pro Woche -> kcal pro Tag: * 7700 / 7
                zeile["tdee"] = round(
                    zeile["kcal_avg"] - zeile["gewicht_diff"] * KCAL_PRO_KG / 7)
        ergebnis.append(zeile)
        if bauch is not None:
            letzter_bauch = bauch

        # Gleitender Wert: Mittel der vorhandenen Wochen-TDEEs der letzten 4 Wochen
        fenster = [z["tdee"] for z in ergebnis[-GLEITEND_WOCHEN:] if z["tdee"] is not None]
        zeile["tdee_gleitend"] = round(sum(fenster) / len(fenster)) if fenster else None
    return ergebnis
