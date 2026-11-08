"""The public service must open the app and direct invitation links on one URL."""

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_spa_serves_direct_links_and_does_not_mask_api_errors(tmp_path):
    from app.web import register_frontend

    (tmp_path / "index.html").write_text("<html><div id='root'>Vendor app</div></html>", encoding="utf-8")
    (tmp_path / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('loaded')", encoding="utf-8")

    app = FastAPI()

    @app.post("/api/invitations", status_code=201)
    def create_invitation():
        return {"created": True}

    @app.get("/api/items")
    def list_items():
        return {"items": []}

    register_frontend(app, tmp_path)
    with TestClient(app) as client:
        assert "Vendor app" in client.get("/").text
        assert "Vendor app" in client.get("/invite/demo-token").text
        assert "Vendor app" in client.get("/invite/demo-token").text  # direct refresh
        assert client.get("/assets/app.js").text == "console.log('loaded')"
        assert client.get("/favicon.svg").status_code == 200
        assert client.get("/api/nonexistent").status_code == 404
        assert client.post("/api/invitations/").status_code == 201
        assert client.get("/api/items/").status_code == 200
        assert client.get("/assets/missing.js").status_code == 404
