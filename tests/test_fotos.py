import io

import pytest
from PIL import Image

import config
import db
import photos


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(config, "XLSX_PATH", tmp_path / "t.xlsx")
    monkeypatch.setattr(config, "PHOTO_DIR", tmp_path / "fotos")
    import app as app_modul
    db.init_db()
    return app_modul.app.test_client()


def jpeg_mit_exif(groesse=(3000, 2000)):
    bild = Image.new("RGB", groesse, (200, 100, 50))
    exif = Image.Exif()
    exif[0x010F] = "TestKamera"
    exif[0x8825] = {1: "N", 2: (50.0, 6.0, 0.0), 3: "E", 4: (8.0, 0.0, 0.0)}  # GPS
    puffer = io.BytesIO()
    bild.save(puffer, "JPEG", exif=exif)
    puffer.seek(0)
    return puffer


def hochladen(client, datum, **dateien):
    daten = {"datum": datum, **{art: (f, "a.jpg") for art, f in dateien.items()}}
    return client.post("/foto", data=daten, content_type="multipart/form-data")


def test_upload_verkleinert_und_entfernt_exif(client):
    original = jpeg_mit_exif()
    assert len(Image.open(original).getexif()) > 0
    original.seek(0)
    assert hochladen(client, "2026-10-05", front=original).status_code == 302
    datei = config.PHOTO_DIR / "2026-10-05_front.jpg"
    bild = Image.open(datei)
    assert max(bild.size) == 1600
    assert len(bild.getexif()) == 0 and "exif" not in bild.info
    assert datei.stat().st_size <= 500_000


def test_kein_bild_und_ungueltige_art(client):
    assert hochladen(client, "2026-10-05", front=io.BytesIO(b"kein bild")).status_code == 400
    assert hochladen(client, "2026-10-05").status_code == 400
    assert not config.PHOTO_DIR.exists() or not list(config.PHOTO_DIR.iterdir())
    with pytest.raises(photos.FotoFehler):
        photos.speichern("2026-10-05", "../x", jpeg_mit_exif())


def test_vergleich_anzeige_ausliefern_loeschen(client):
    for datum in ("2026-10-01", "2026-10-05"):
        hochladen(client, datum, side=jpeg_mit_exif((800, 600)))
    seite = client.get("/vergleich").text
    assert "Woche 1" in seite and "Woche 2" in seite and "2026-10-05_side.jpg" in seite
    assert client.get("/foto/2026-10-05_side.jpg").status_code == 200
    assert client.get("/foto/..%2Ftracker.db").status_code == 404
    client.post("/foto/loeschen", data={"datum": "2026-10-05", "art": "side"})
    assert client.get("/foto/2026-10-05_side.jpg").status_code == 404
    assert client.get("/vergleich?a=99").status_code == 200
