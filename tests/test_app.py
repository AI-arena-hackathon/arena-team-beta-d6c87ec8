"""Tests for the Local Lens AI Analytics core API."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import Recommendation, create_app, recompute_and_store


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


def test_recommendations_exclude_sales_older_than_forecast_window(tmp_path):
    client = make_client(tmp_path)
    stale = client.post(
        "/ingest",
        json=[
            {
                "date": (datetime.now() - timedelta(days=45)).isoformat(),
                "item_id": "rice",
                "qty": 50,
                "price": 2.5,
            }
        ],
    )
    assert stale.status_code == 201
    stock = client.put("/stock", json={"item_id": "rice", "qty": 5})
    assert stock.status_code == 200
    response = client.get("/recommendations")
    assert response.status_code == 200
    assert response.json() == []


def test_recommendations_forecast_ignores_sales_outside_window(tmp_path):
    client = make_client(tmp_path)
    stale = client.post(
        "/ingest",
        json=[
            {
                "date": (datetime.now() - timedelta(days=40)).isoformat(),
                "item_id": "rice",
                "qty": 50,
                "price": 2.5,
            }
        ],
    )
    assert stale.status_code == 201
    fresh = client.post(
        "/ingest",
        json=[
            {
                "date": (datetime.now() - timedelta(days=2)).isoformat(),
                "item_id": "rice",
                "qty": 3,
                "price": 2.5,
            }
        ],
    )
    assert fresh.status_code == 201
    stock = client.put("/stock", json={"item_id": "rice", "qty": 30})
    assert stock.status_code == 200
    response = client.get("/recommendations")
    assert response.status_code == 200
    # Only the fresh 3-unit sale is in the 30-day window; its weekly forecast
    # (~21 units) stays under the stock threshold (~24), so no alert fires.
    # A stale high-volume sale inside the history must not inflate the forecast.
    assert response.json() == []


def _sell(client, item_id: str, qty_per_day: int, days: int = 10) -> None:
    rows = [
        {"date": (datetime.now() - timedelta(days=d)).isoformat(), "item_id": item_id, "qty": qty_per_day, "price": 2.5}
        for d in range(1, days + 1)
    ]
    response = client.post("/ingest", json=rows)
    assert response.status_code == 201


def test_stock_upsert_creates_then_updates(tmp_path):
    client = make_client(tmp_path)
    created = client.put("/stock", json={"item_id": "rice", "qty": 7})
    assert created.status_code == 200
    assert created.json() == {"item_id": "rice", "qty": 7}

    updated = client.put("/stock", json={"item_id": "rice", "qty": 2})
    assert updated.status_code == 200
    assert updated.json() == {"item_id": "rice", "qty": 2}

    other = client.put("/stock", json={"item_id": "beans", "qty": 4})
    assert other.status_code == 200
    assert other.json() == {"item_id": "beans", "qty": 4}


def test_stock_update_rejects_negative_qty(tmp_path):
    client = make_client(tmp_path)
    response = client.put("/stock", json={"item_id": "rice", "qty": -1})
    assert response.status_code == 422


def test_alert_settings_default_when_unset(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/settings")
    assert response.status_code == 200
    assert response.json() == {"phone": "", "threshold": None, "enabled": True}


def test_alert_settings_update_persists_round_trip(tmp_path):
    client = make_client(tmp_path)
    put = client.put("/settings", json={"phone": "+15550001111", "threshold": 12.5, "enabled": False})
    assert put.status_code == 200
    assert put.json() == {"phone": "+15550001111", "threshold": 12.5, "enabled": False}
    get = client.get("/settings")
    assert get.status_code == 200
    assert get.json() == {"phone": "+15550001111", "threshold": 12.5, "enabled": False}


def test_alert_settings_reject_negative_threshold(tmp_path):
    client = make_client(tmp_path)
    response = client.put("/settings", json={"phone": "+15550001111", "threshold": -1, "enabled": True})
    assert response.status_code == 422


def test_alert_disabled_does_not_send(tmp_path):
    client = make_client(tmp_path)
    _sell(client, "rice", 3)
    client.put("/stock", json={"item_id": "rice", "qty": 5})
    client.put("/settings", json={"phone": "+15550001111", "threshold": 10, "enabled": False})
    sent = client.post("/alerts", json={"item_id": "rice"})
    assert sent.status_code == 200
    assert sent.json()["sent"] is False


def test_alert_unknown_item_returns_no_recommendation(tmp_path):
    client = make_client(tmp_path)
    sent = client.post("/alerts", json={"item_id": "ghost"})
    assert sent.status_code == 200
    assert sent.json()["sent"] is False
    assert sent.json()["reason"] == "no_recommendation"


def test_recompute_stores_recommendations_with_created_at(tmp_path):
    client = make_client(tmp_path)
    _sell(client, "rice", 3)
    client.put("/stock", json={"item_id": "rice", "qty": 5})
    recompute_and_store(client.app.state.engine)
    with Session(client.app.state.engine) as session:
        stored = session.exec(select(Recommendation)).all()
    assert len(stored) == 1
    assert stored[0].created_at is not None


def test_ingest_rejects_negative_price_and_accepts_alias_and_multi_item(tmp_path):
    client = make_client(tmp_path)
    bad = client.post(
        "/ingest",
        json=[{"date": "2026-11-01T09:00:00", "item_id": "rice", "qty": 1, "price": -1}],
    )
    assert bad.status_code == 422
    alias = client.post(
        "/ingest",
        json=[{"date": "2026-11-01T09:00:00", "item-id": "rice", "qty": 2, "price": 1.5}],
    )
    assert alias.status_code == 201
    multi = client.post(
        "/ingest",
        json=[
            {"date": "2026-11-01T09:00:00", "item_id": "rice", "qty": 1, "price": 2.5},
            {"date": "2026-11-01T10:00:00", "item_id": "beans", "qty": 2, "price": 1.5},
        ],
    )
    assert multi.status_code == 201
    assert multi.json()["ingested"] == 2


def test_recommendations_return_at_most_top_five_sorted_by_forecast(tmp_path):
    client = make_client(tmp_path)
    for i in range(1, 7):
        _sell(client, f"item-{i}", 3 * i)
        client.put("/stock", json={"item_id": f"item-{i}", "qty": 1})
    response = client.get("/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    forecasts = [r["forecast_qty"] for r in data]
    assert forecasts == sorted(forecasts, reverse=True)


def test_recommendation_reports_reorder_qty_and_confidence(tmp_path):
    client = make_client(tmp_path)
    _sell(client, "rice", 3)
    client.put("/stock", json={"item_id": "rice", "qty": 5})
    response = client.get("/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    recommendation = data[0]
    forecast_qty = recommendation["forecast_qty"]
    assert forecast_qty == 21.0
    assert recommendation["reorder_qty"] == 16.0
    assert recommendation["confidence"] == 0.71
