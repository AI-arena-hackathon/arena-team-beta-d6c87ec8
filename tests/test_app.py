"""Tests for the Local Lens AI Analytics core API."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app import create_app


def make_client(tmp_path):
    app = create_app(f"sqlite:////{tmp_path}/test.db")
    return TestClient(app)


def test_health_returns_ok(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_rejects_non_positive_qty(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/ingest",
        json=[{"date": "2026-11-01T09:00:00", "item_id": "rice", "qty": 0, "price": 2.5}],
    )
    assert response.status_code == 422


def test_ingest_persists_sales_and_reports_count(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/ingest",
        json=[{"date": "2026-11-01T09:00:00", "item_id": "rice", "qty": 3, "price": 2.5}],
    )
    assert response.status_code == 201
    assert response.json()["ingested"] == 1


def test_sync_marks_pending_sales_synced(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/ingest",
        json=[{"date": "2026-11-01T09:00:00", "item_id": "rice", "qty": 3, "price": 2.5}],
    )
    assert response.status_code == 201
    sync = client.post("/sync")
    assert sync.status_code == 200
    assert sync.json()["synced"] == 1


def test_recommendations_empty_when_no_sales(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/recommendations")
    assert response.status_code == 200
    assert response.json() == []


def test_recommendations_flag_item_forecasted_above_stock_threshold(tmp_path):
    client = make_client(tmp_path)
    rows = [
        {"date": (datetime.now() - timedelta(days=d)).isoformat(), "item_id": "rice", "qty": 3, "price": 2.5}
        for d in range(1, 11)
    ]
    ingest = client.post("/ingest", json=rows)
    assert ingest.status_code == 201
    stock = client.put("/stock", json={"item_id": "rice", "qty": 5})
    assert stock.status_code == 200
    response = client.get("/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    recommendation = data[0]
    assert recommendation["item_id"] == "rice"
    # 3 units/day over 10 days => 7-unit weekly forecast vs stock 5
    # (flag when forecast > stock * 0.8, i.e. > 4).
    assert recommendation["forecast_qty"] > 4


def test_alert_respects_enabled_threshold(tmp_path):
    client = make_client(tmp_path)
    client.post(
        "/ingest",
        json=[
            {"date": (datetime.now() - timedelta(days=d)).isoformat(), "item_id": "rice", "qty": 3, "price": 2.5}
            for d in range(1, 11)
        ],
    )
    client.put("/stock", json={"item_id": "rice", "qty": 5})
    client.put("/settings", json={"phone": "+15550001111", "threshold": 50, "enabled": True})
    sent = client.post("/alerts", json={"item_id": "rice"})
    assert sent.status_code == 200
    assert sent.json()["sent"] is False


def test_alert_sends_when_forecast_crosses_threshold(tmp_path):
    client = make_client(tmp_path)
    client.post(
        "/ingest",
        json=[
            {"date": (datetime.now() - timedelta(days=d)).isoformat(), "item_id": "rice", "qty": 3, "price": 2.5}
            for d in range(1, 11)
        ],
    )
    client.put("/stock", json={"item_id": "rice", "qty": 5})
    client.put("/settings", json={"phone": "+15550001111", "threshold": 10, "enabled": True})
    sent = client.post("/alerts", json={"item_id": "rice"})
    assert sent.status_code == 200
    body = sent.json()
    assert body["sent"] is True
    assert body["provider"] == "mock"
    assert body["to"] == "+15550001111"


def test_index_serves_accessible_html_with_skip_link(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert 'lang="en"' in html
    assert 'href="#main-content"' in html
    assert 'id="main-content"' in html


def test_recommendations_list_is_polite_live_region(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/")
    assert response.status_code == 200
    assert '<ol id="recommendations" aria-live="polite">' in response.text


def test_restock_chart_has_accessible_name(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/")
    assert response.status_code == 200
    assert 'setAttribute("role", "img")' in response.text
    assert 'setAttribute("aria-label"' in response.text
