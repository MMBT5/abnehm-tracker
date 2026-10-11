"""Konfiguration über Umgebungsvariablen, mit Defaults für lokale Entwicklung."""
import os
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Im Container zeigen die Variablen auf das gemountete Samba-Verzeichnis (z. B. /data).
DB_PATH = Path(os.environ.get("DB_PATH", BASE_DIR / "data" / "tracker.db"))
XLSX_PATH = Path(os.environ.get("XLSX_PATH", BASE_DIR / "data" / "tracker.xlsx"))
PHOTO_DIR = Path(os.environ.get("PHOTO_DIR", BASE_DIR / "data" / "fotos"))

# Tag 1 = Montag, damit Wochen Mo-So laufen. Tag 1-3 (28.-30.09.) sind Platzhalter
# aus der Excel-Tabelle, echte Daten beginnen mit Tag 4 = 01.10.
START_DATE = date.fromisoformat(os.environ.get("START_DATE", "2026-09-28"))
