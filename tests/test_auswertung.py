from datetime import date, timedelta

import pytest

from auswertung import tag_nr, wochen_auswertung, wochen_nr

START = date(2026, 9, 28)  # Montag


def tag(n, **werte):
    """Eintrag für Tag n (Tag 1 = START)."""
    e = {"datum": (START + timedelta(days=n - 1)).isoformat(),
         "kcal": None, "gewicht": None, "protein": None, "bauch": None}
    e.update(werte)
    return e


def test_tag_und_woche():
    assert tag_nr(date(2026, 9, 28), START) == 1
    assert wochen_nr(date(2026, 9, 28), START) == 1
    assert wochen_nr(date(2026, 10, 4), START) == 1    # Sonntag = Ende Woche 1
    assert wochen_nr(date(2026, 10, 5), START) == 2    # Montag = Beginn Woche 2
    assert tag_nr(date(2026, 10, 11), START) == 14
    assert wochen_nr(date(2026, 10, 11), START) == 2


def test_leer():
    assert wochen_auswertung([], START) == []


def test_mittel_und_anzahl_ignorieren_null():
    w = wochen_auswertung([tag(4, kcal=1800, gewicht=122.0), tag(5, kcal=2000),
                           tag(6, gewicht=121.0)], START)[0]
    assert w["kcal_avg"] == 1900 and w["n_kcal"] == 2
    assert w["gewicht_avg"] == 121.5 and w["n_wiegungen"] == 2


def test_differenz_zur_vorwoche():
    w = wochen_auswertung([tag(4, gewicht=122.0), tag(11, gewicht=120.4)], START)
    assert w[0]["gewicht_diff"] is None
    assert w[1]["gewicht_diff"] == pytest.approx(-1.6)


def test_luecke_woche_bleibt_leer_und_vorwoche_ist_leer():
    w = wochen_auswertung([tag(1, gewicht=100.0), tag(15, gewicht=99.0)], START)
    assert [z["woche"] for z in w] == [1, 2, 3]
    assert w[1]["gewicht_avg"] is None
    assert w[2]["gewicht_diff"] is None


def test_bauch_letzter_wert_und_diff_zur_letzten_woche_mit_wert():
    w = wochen_auswertung([tag(2, bauch=110.0), tag(3, bauch=109.0),
                           tag(16, bauch=107.5)], START)  # Woche 1 und 3
    assert w[0]["bauch"] == 109.0 and w[0]["bauch_diff"] is None
    assert w[1]["bauch"] is None
    assert w[2]["bauch_diff"] == -1.5


def test_tage_vor_start_werden_ignoriert():
    e = tag(1, kcal=1000)
    e["datum"] = "2026-09-27"
    assert wochen_auswertung([e], START) == []


def _woche_mit_wiegungen(woche, gewicht, kcal, n=4):
    erster = (woche - 1) * 7 + 1
    return [tag(erster + i, gewicht=gewicht, kcal=kcal) for i in range(n)]


def test_tdee_formel():
    # Woche 2: -0.5 kg Ø, 2000 kcal -> 2000 + 0.5*7700/7 = 2550
    daten = (_woche_mit_wiegungen(1, 100.0, 2000) + _woche_mit_wiegungen(2, 100.0, 2000)
             + _woche_mit_wiegungen(3, 99.5, 2000))
    w = wochen_auswertung(daten, START)
    assert w[0]["tdee"] is None and w[1]["tdee"] is None  # vor Woche 3
    assert w[2]["tdee"] == 2550


def test_tdee_braucht_mindestens_4_wiegungen_in_beiden_wochen():
    daten = (_woche_mit_wiegungen(1, 100.0, 2000) + _woche_mit_wiegungen(2, 100.0, 2000)
             + _woche_mit_wiegungen(3, 99.5, 2000, n=3))
    assert wochen_auswertung(daten, START)[2]["tdee"] is None
    daten = (_woche_mit_wiegungen(1, 100.0, 2000) + _woche_mit_wiegungen(2, 100.0, 2000, n=3)
             + _woche_mit_wiegungen(3, 99.5, 2000))
    assert wochen_auswertung(daten, START)[2]["tdee"] is None


def test_tdee_gleitend_mittelt_vorhandene_wochen():
    daten = (_woche_mit_wiegungen(1, 100.0, 2000) + _woche_mit_wiegungen(2, 100.0, 2000)
             + _woche_mit_wiegungen(3, 99.5, 2000)    # tdee 2550
             + _woche_mit_wiegungen(4, 99.5, 2000))   # tdee 2000
    w = wochen_auswertung(daten, START)
    assert w[3]["tdee"] == 2000
    assert w[3]["tdee_gleitend"] == 2275
