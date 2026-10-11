import pytest

import config
import db


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    import app as app_modul
    db.init_db()
    return app_modul.app.test_client()


def test_speichern_komma_und_leere_felder_ueberschreiben_nicht(client):
    client.post("/speichern", data={"datum": "2026-10-05", "gewicht": "121,5", "kcal": "1800"})
    client.post("/speichern", data={"datum": "2026-10-05", "gewicht": "", "protein": "140"})
    e = db.tag_holen("2026-10-05")
    assert (e["gewicht"], e["kcal"], e["protein"]) == (121.5, 1800, 140)


def test_ungueltige_eingaben(client):
    for daten in ({"datum": "2026-10-05", "gewicht": "abc"},
                  {"datum": "2026-10-05", "kcal": "1800.5"},
                  {"datum": "2026-10-05", "gewicht": "5"},
                  {"datum": "2999-01-01", "kcal": "1800"},
                  {"datum": "2026-10-05"}):
        assert client.post("/speichern", data=daten).status_code == 400
    assert db.alle() == []


def test_loeschen_und_seiten(client):
    client.post("/speichern", data={"datum": "2026-10-05", "gewicht": "121.5", "kcal": "1800"})
    assert 'value="121,5"' in client.get("/?datum=2026-10-05").text
    client.post("/loeschen", data={"datum": "2026-10-05", "feld": "gewicht"})
    assert db.tag_holen("2026-10-05")["gewicht"] is None
    assert client.post("/loeschen", data={"datum": "2026-10-05", "feld": "datum"}).status_code == 400
    assert client.get("/wochen").status_code == 200
    assert client.get("/static/manifest.json").status_code == 200
