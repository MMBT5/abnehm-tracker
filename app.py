"""Flask-App: Eingabeformular, letzte 14 Tage, Wochenauswertung."""
import os
from datetime import date, timedelta

from flask import Flask, redirect, render_template, request, url_for

import auswertung
import chart
import config
import db
import excel_export

app = Flask(__name__)
db.init_db()  # idempotent (CREATE TABLE IF NOT EXISTS)
excel_export.exportieren()  # Datei beim Start auf Stand bringen

# Formularfeld -> (Typ, Minimum, Maximum, Anzeigename); Grenzen nur gegen Tippfehler
FELD_REGELN = {
    "gewicht": (float, 30, 400, "Gewicht"),
    "kcal": (int, 1, 20000, "Kalorien"),
    "protein": (int, 1, 1000, "Protein"),
    "bauch": (float, 30, 300, "Bauch"),
}
ANZEIGE = {"gewicht": "Gewicht", "kcal": "Kalorien", "protein": "Protein", "bauch": "Bauch"}


@app.template_filter("de")
def zahl_de(wert, stellen=1, vorzeichen=False):
    """Zahl mit Komma; None -> Gedankenstrich."""
    if wert is None:
        return "–"
    text = f"{wert:+.{stellen}f}" if vorzeichen else f"{wert:.{stellen}f}"
    return text.replace(".", ",")


@app.template_filter("kurz")
def datum_kurz(d):
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return d.strftime("%d.%m.")


def parse_zahl(text, typ):
    """'' -> None (nicht erfasst, NICHT 0). Komma und Punkt als Dezimaltrenner."""
    text = (text or "").strip().replace(",", ".")
    if not text:
        return None
    zahl = float(text)
    if typ is int:
        if zahl != int(zahl):
            raise ValueError("ganze Zahl erwartet")
        return int(zahl)
    return zahl


def parse_formular(form):
    """Gibt (datum, werte, fehler) zurück."""
    fehler = []
    try:
        datum = date.fromisoformat(form.get("datum", ""))
        if datum > date.today():
            fehler.append("Das Datum liegt in der Zukunft.")
    except ValueError:
        datum = None
        fehler.append("Ungültiges Datum.")
    werte = {}
    for feld, (typ, lo, hi, name) in FELD_REGELN.items():
        try:
            wert = parse_zahl(form.get(feld), typ)
        except ValueError:
            fehler.append(f"{name}: keine gültige Zahl.")
            continue
        if wert is not None and not lo <= wert <= hi:
            fehler.append(f"{name}: {wert:g} ist unplausibel.")
            continue
        werte[feld] = wert
    return datum, werte, fehler


def letzte_tage(n=14):
    """Die letzten n Kalendertage (heute zuerst), auch ohne Eintrag, damit Lücken sichtbar sind."""
    heute = date.today()
    von = heute - timedelta(days=n - 1)
    vorhanden = {r["datum"]: r for r in db.zeitraum(von.isoformat(), heute.isoformat())}
    tage = []
    for i in range(n):
        d = heute - timedelta(days=i)
        tage.append({"datum": d, "iso": d.isoformat(), "eintrag": vorhanden.get(d.isoformat()),
                     "tag": auswertung.tag_nr(d, config.START_DATE)})
    return tage


def seite(datum, werte=None, meldung=None, fehler=None):
    """Startseite rendern; werte = Formularinhalt (sonst der gespeicherte Tag)."""
    gespeichert = db.tag_holen(datum.isoformat())
    if werte is None:  # gespeicherter Tag -> als Text fürs Formular (Komma, leer statt None)
        werte = {f: zahl_de(gespeichert[f], 1) if gespeichert and gespeichert[f] is not None
                 and f in ("gewicht", "bauch") else (gespeichert[f] if gespeichert else "")
                 for f in db.FELDER}
    werte = {f: "" if werte.get(f) is None else werte.get(f) for f in db.FELDER}
    return render_template(
        "index.html", datum=datum.isoformat(), werte=werte, gespeichert=gespeichert,
        tage=letzte_tage(), meldung=meldung, excel_fehler=excel_export.letzter_fehler, fehler=fehler or [], anzeige=ANZEIGE,
        tag=auswertung.tag_nr(datum, config.START_DATE),
        woche=auswertung.wochen_nr(datum, config.START_DATE))


@app.get("/")
def index():
    try:
        datum = date.fromisoformat(request.args.get("datum", ""))
    except ValueError:
        datum = date.today()
    meldung = "Gespeichert." if request.args.get("ok") else None
    if request.args.get("excel") == "ok":
        meldung = "Excel wurde neu erzeugt."
    return seite(datum, meldung=meldung)


@app.post("/speichern")
def speichern():
    datum, werte, fehler = parse_formular(request.form)
    if fehler:
        return seite(datum or date.today(), werte=request.form, fehler=fehler), 400
    if all(v is None for v in werte.values()):
        return seite(datum, fehler=["Kein Wert eingegeben."]), 400
    db.speichern(datum.isoformat(), **werte)
    excel_export.exportieren()  # Fehler landen in excel_export.letzter_fehler, Eintrag bleibt in der DB
    return redirect(url_for("index", datum=datum.isoformat(), ok=1))


@app.post("/loeschen")
def loeschen():
    """Einzelnen Wert bewusst auf NULL setzen (leeres Feld im Formular tut das nicht)."""
    feld = request.form.get("feld", "")
    if feld not in db.FELDER:
        return "Unbekanntes Feld", 400
    db.wert_loeschen(request.form["datum"], feld)
    excel_export.exportieren()
    return redirect(url_for("index", datum=request.form["datum"]))


@app.post("/excel")
def excel_neu():
    erfolg = excel_export.exportieren()
    return redirect(url_for("index", excel="ok" if erfolg else "fehler"))


@app.get("/wochen")
def wochen():
    eintraege = db.alle()
    zeilen = auswertung.wochen_auswertung(eintraege, config.START_DATE)
    verlauf = chart.gewichtsverlauf_svg(eintraege, zeilen, config.START_DATE)
    return render_template("wochen.html", zeilen=reversed(zeilen), verlauf=verlauf)


if __name__ == "__main__":
    # Nur für lokale Entwicklung; im Container läuft später gunicorn.
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 8099)),
            debug=bool(os.environ.get("FLASK_DEBUG")))
