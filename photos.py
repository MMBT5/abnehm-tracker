"""Wochenfotos: verkleinern, EXIF (inkl. GPS) entfernen, als Datei in PHOTO_DIR ablegen.
Fotos stehen weder in der DB noch in der Excel-Datei."""
import os
import re
import tempfile
from datetime import date

from PIL import Image, ImageOps, UnidentifiedImageError

import auswertung
import config

ARTEN = {"front": "Vorderansicht", "side": "Seitenansicht"}
MAX_KANTE = 1600
ZIEL_BYTES = 500_000
DATEI_MUSTER = re.compile(r"^(\d{4}-\d{2}-\d{2})_(front|side)\.jpg$")

Image.MAX_IMAGE_PIXELS = 100_000_000  # Schutz vor Dekompressionsbomben


class FotoFehler(ValueError):
    pass


def dateiname(datum, art):
    return f"{datum}_{art}.jpg"


def speichern(datum, art, stream):
    """datum als ISO-String. Überschreibt ein vorhandenes Foto desselben Tages/derselben Art."""
    if art not in ARTEN:
        raise FotoFehler("Unbekannte Fotoart.")
    try:
        bild = Image.open(stream)
        bild.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise FotoFehler("Das ist kein lesbares Bild.")
    # Orientierung aus EXIF anwenden, bevor die EXIF-Daten wegfallen (sonst liegen Handyfotos quer)
    bild = ImageOps.exif_transpose(bild).convert("RGB")
    bild.thumbnail((MAX_KANTE, MAX_KANTE))

    config.PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    ziel = config.PHOTO_DIR / dateiname(datum, art)
    fd, tmp = tempfile.mkstemp(dir=config.PHOTO_DIR, prefix=".foto-", suffix=".tmp")
    os.close(fd)
    try:
        # Neu gespeichert ohne exif=… -> keine Metadaten (GPS, Kamera, Zeit) in der Datei
        for qualitaet in (85, 78, 70, 62, 55):
            bild.save(tmp, "JPEG", quality=qualitaet, optimize=True)
            if os.path.getsize(tmp) <= ZIEL_BYTES:
                break
        os.replace(tmp, ziel)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def loeschen(datum, art):
    if art in ARTEN:
        (config.PHOTO_DIR / dateiname(datum, art)).unlink(missing_ok=True)


def alle():
    """Alle Fotos als {(datum, art)}."""
    if not config.PHOTO_DIR.is_dir():
        return set()
    treffer = (DATEI_MUSTER.match(n) for n in os.listdir(config.PHOTO_DIR))
    return {(m.group(1), m.group(2)) for m in treffer if m}


def tag_fotos(datum):
    return {art: dateiname(datum, art) for d, art in alle() if d == datum}


def nach_wochen():
    """{woche: {art: (datum, dateiname)}} -- je Woche das jeweils späteste Foto pro Art."""
    wochen = {}
    for d, art in sorted(alle()):
        w = auswertung.wochen_nr(date.fromisoformat(d), config.START_DATE)
        if w >= 1:
            wochen.setdefault(w, {})[art] = (d, dateiname(d, art))
    return wochen
