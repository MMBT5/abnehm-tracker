"""SQLite-Zugriff: Schema, Upsert, Abfragen. Bewusst ohne ORM, damit das SQL sichtbar bleibt."""
import sqlite3
from contextlib import closing

import config

# Erlaubte Messwert-Spalten. Spaltennamen kann man NICHT mit "?" parametrisieren,
# deshalb prüfen wir sie gegen diese feste Liste, bevor wir sie ins SQL einsetzen.
FELDER = ("kcal", "gewicht", "protein", "bauch")

# CREATE TABLE IF NOT EXISTS: legt die Tabelle nur an, wenn sie fehlt -> beim
# App-Start jedes Mal gefahrlos ausführbar (idempotent).
# datum ist PRIMARY KEY: pro Tag genau eine Zeile.
# Spalten ohne NOT NULL dürfen leer (NULL) sein. NULL heißt "nicht erfasst",
# etwas anderes als 0 -- sonst würde ein Tag ohne Eintrag den Kalorienschnitt drücken.
SCHEMA = """
CREATE TABLE IF NOT EXISTS eintraege (
    datum   TEXT PRIMARY KEY,
    kcal    INTEGER,
    gewicht REAL,
    protein INTEGER,
    bauch   REAL
)
"""

# Upsert = INSERT, und falls das Datum schon existiert (ON CONFLICT), stattdessen UPDATE.
# "excluded" ist die Zeile, die wir gerade einfügen wollten.
# COALESCE(a, b) liefert a, falls a nicht NULL ist, sonst b:
#   neuer Wert vorhanden -> übernehmen, leeres Formularfeld -> alten Wert behalten.
UPSERT = """
INSERT INTO eintraege (datum, kcal, gewicht, protein, bauch)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(datum) DO UPDATE SET
    kcal    = COALESCE(excluded.kcal,    kcal),
    gewicht = COALESCE(excluded.gewicht, gewicht),
    protein = COALESCE(excluded.protein, protein),
    bauch   = COALESCE(excluded.bauch,   bauch)
"""


def verbinden():
    """Neue Verbindung; Zeilen sind per Spaltenname ansprechbar (row["kcal"])."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(verbinden()) as conn, conn:
        conn.execute(SCHEMA)


def speichern(datum, kcal=None, gewicht=None, protein=None, bauch=None):
    """Legt den Tag an oder ergänzt ihn. None = Feld unverändert lassen."""
    # "?" sind Platzhalter: sqlite3 setzt die Werte selbst und sicher ein.
    # Würde man sie per f-String ins SQL schreiben, könnte ein präparierter Wert
    # eigenes SQL einschleusen (SQL-Injection).
    with closing(verbinden()) as conn, conn:  # "with conn" = Transaktion: commit/rollback
        conn.execute(UPSERT, (datum, kcal, gewicht, protein, bauch))


def wert_loeschen(datum, feld):
    """Setzt einen einzelnen Wert bewusst auf NULL (das Formular kann das nicht)."""
    if feld not in FELDER:
        raise ValueError(f"Unbekanntes Feld: {feld!r}")
    with closing(verbinden()) as conn, conn:
        conn.execute(f"UPDATE eintraege SET {feld} = NULL WHERE datum = ?", (datum,))


def tag_holen(datum):
    with closing(verbinden()) as conn:
        return conn.execute("SELECT * FROM eintraege WHERE datum = ?", (datum,)).fetchone()


def zeitraum(von, bis):
    """Alle Einträge von..bis (beide inklusive), älteste zuerst."""
    # Das Vergleichen mit >= / <= funktioniert, weil ISO-Daten (YYYY-MM-DD) als Text
    # genauso sortieren wie chronologisch: erst Jahr, dann Monat, dann Tag.
    with closing(verbinden()) as conn:
        return conn.execute(
            "SELECT * FROM eintraege WHERE datum BETWEEN ? AND ? ORDER BY datum",
            (von, bis),
        ).fetchall()


def alle():
    with closing(verbinden()) as conn:
        return conn.execute("SELECT * FROM eintraege ORDER BY datum").fetchall()


def letzte(n=14):
    """Die letzten n Einträge, neueste zuerst."""
    with closing(verbinden()) as conn:
        return conn.execute(
            "SELECT * FROM eintraege ORDER BY datum DESC LIMIT ?", (n,)
        ).fetchall()
