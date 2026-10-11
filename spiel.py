"""Spielwiese zum Ausprobieren von db.py. Nutzt eine eigene Wegwerf-DB, nicht tracker.db.

Start: python spiel.py
"""
import config
from pathlib import Path

config.DB_PATH = Path(__file__).resolve().parent / "data" / "spiel.db"
config.DB_PATH.unlink(missing_ok=True)

import db  # noqa: E402  (erst nach dem Umbiegen des Pfads importieren)


def zeige(titel):
    print(f"\n--- {titel}")
    for r in db.alle():
        print(dict(r))


db.init_db()
db.init_db()  # zweiter Aufruf ist harmlos (IF NOT EXISTS)

db.speichern("2026-10-05", kcal=1800, gewicht=121.5)
zeige("1) Neuer Tag angelegt")

db.speichern("2026-10-05", protein=140)
zeige("2) Protein ergänzt; kcal und gewicht bleiben (COALESCE)")

db.speichern("2026-10-05", kcal=1900)
zeige("3) kcal korrigiert (UPDATE statt zweiter Zeile)")

db.wert_loeschen("2026-10-05", "gewicht")
zeige("4) Gewicht bewusst gelöscht -> NULL (None), nicht 0")

db.speichern("2026-10-06", kcal=2000)
db.speichern("2026-10-07", gewicht=121.0)
print("\n--- 5) Zeitraum 06.-07.10.")
for r in db.zeitraum("2026-10-06", "2026-10-07"):
    print(dict(r))

print("\n--- 6) Letzte 2 Einträge, neueste zuerst")
for r in db.letzte(2):
    print(dict(r))

print("\nTipp: sqlite3-Shell? 'python -m sqlite3 data/spiel.db' und dort 'SELECT * FROM eintraege;'")
