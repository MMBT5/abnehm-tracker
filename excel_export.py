"""Excel-Export. Die Datei ist nur eine Ausgabe und wird immer komplett aus der DB neu erzeugt."""
import logging
import os
import tempfile
import threading
from datetime import date, timedelta

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

import auswertung
import config
import db

log = logging.getLogger(__name__)

_sperre = threading.Lock()
# Ergebnis des letzten Versuchs; die UI zeigt den Hinweis, solange hier ein Fehler steht.
letzter_fehler = None

KOPF = Font(bold=True, color="FFFFFF")
KOPF_FUELLUNG = PatternFill("solid", fgColor="2F3B4C")
DUENN = Side(style="thin", color="BBBBBB")
DICK = Side(style="medium", color="000000")


def _kopfzeile(ws, titel):
    ws.append(titel)
    for zelle in ws[1]:
        zelle.font, zelle.fill = KOPF, KOPF_FUELLUNG
        zelle.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"


def _blatt_tage(ws, eintraege, start):
    ws.title = "Tage"
    _kopfzeile(ws, ["Woche", "Tag", "Datum", "Kalorien", "Protein", "Gewicht morgens", "Bauch"])
    nach_datum = {e["datum"]: e for e in eintraege}
    letzte_woche = auswertung.wochen_nr(
        max([date.today()] + [date.fromisoformat(e["datum"]) for e in eintraege]), start)

    zeile = 2
    for woche in range(1, letzte_woche + 1):
        erste = zeile
        for i in range(7):
            tag = (woche - 1) * 7 + i + 1
            d = start + timedelta(days=tag - 1)
            e = nach_datum.get(d.isoformat())
            ws.append([woche, tag, d,
                       e["kcal"] if e else None, e["protein"] if e else None,
                       e["gewicht"] if e else None, e["bauch"] if e else None])
            ws.cell(zeile, 3).number_format = "DD.MM.YYYY"
            ws.cell(zeile, 6).number_format = "0.0"
            ws.cell(zeile, 7).number_format = "0.0"
            for spalte in range(1, 8):
                ws.cell(zeile, spalte).border = Border(
                    top=DICK if i == 0 else DUENN, bottom=DICK if i == 6 else DUENN,
                    left=DUENN, right=DUENN)
            zeile += 1
        # Woche als verbundene Zelle über die 7 Tage
        ws.merge_cells(start_row=erste, start_column=1, end_row=zeile - 1, end_column=1)
        ws.cell(erste, 1).alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(erste, 1).font = Font(bold=True)
    for spalte, breite in zip("ABCDEFG", (8, 6, 13, 10, 9, 16, 8)):
        ws.column_dimensions[spalte].width = breite


def _blatt_wochen(ws, eintraege, start):
    ws.title = "Wochen"
    _kopfzeile(ws, ["Woche", "Von", "Bis", "Ø Gewicht", "Wiegungen", "Δ Gewicht",
                    "Ø kcal", "Tage mit kcal", "Ø Protein", "Bauch", "Δ Bauch",
                    "TDEE (Woche)", "TDEE (gleitend)"])
    for z in auswertung.wochen_auswertung(eintraege, start):
        ws.append([z["woche"], z["von"], z["bis"], z["gewicht_avg"], z["n_wiegungen"],
                   z["gewicht_diff"], z["kcal_avg"], z["n_kcal"], z["protein_avg"],
                   z["bauch"], z["bauch_diff"], z["tdee"], z["tdee_gleitend"]])
        r = ws.max_row
        for spalte in (2, 3):
            ws.cell(r, spalte).number_format = "DD.MM.YYYY"
        for spalte, fmt in ((4, "0.00"), (6, "+0.00;-0.00;0.00"), (7, "0"), (9, "0"),
                            (10, "0.0"), (11, "+0.0;-0.0;0.0"), (12, "0"), (13, "0")):
            ws.cell(r, spalte).number_format = fmt
    for spalte in range(1, 14):
        ws.column_dimensions[ws.cell(1, spalte).column_letter].width = 13
    ws.row_dimensions[1].height = 32


def _schreiben(ziel):
    eintraege = [dict(e) for e in db.alle()]
    wb = Workbook()
    _blatt_tage(wb.active, eintraege, config.START_DATE)
    _blatt_wochen(wb.create_sheet(), eintraege, config.START_DATE)

    ziel.parent.mkdir(parents=True, exist_ok=True)
    # Temp-Datei im selben Ordner, damit os.replace atomar ist (gleiches Dateisystem).
    fd, tmp = tempfile.mkstemp(dir=ziel.parent, prefix=".tracker-", suffix=".tmp")
    os.close(fd)
    try:
        wb.save(tmp)
        os.replace(tmp, ziel)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def exportieren():
    """Erzeugt die Excel-Datei neu. Wirft nie: bei Fehler (z. B. Datei in Excel offen)
    wird geloggt, letzter_fehler gesetzt und False zurückgegeben. Die DB bleibt unberührt."""
    global letzter_fehler
    with _sperre:
        try:
            _schreiben(config.XLSX_PATH)
        except OSError as fehler:  # PermissionError ist eine OSError
            letzter_fehler = str(fehler)
            log.error("Excel-Export fehlgeschlagen (%s): %s", config.XLSX_PATH, fehler)
            return False
        letzter_fehler = None
        return True
