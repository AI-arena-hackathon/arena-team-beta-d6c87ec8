"""Local Lens AI Analytics — offline-first POS restock engine."""

import asyncio
import os
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import AliasChoices, BaseModel, field_validator
from sqlalchemy import Engine
from sqlmodel import Field, Index, Session, SQLModel, create_engine, select

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data.db")
FORECAST_WINDOW_DAYS = 30
FORECAST_HORIZON_DAYS = 7
RESTOCK_FRACTION = 0.8


class Sale(SQLModel, table=True):
    __table_args__ = (Index("ix_sales_date", "date"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime
    item_id: str
    qty: int
    price: float
    synced_at: Optional[datetime] = None


class Stock(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: str
    qty: int


class Recommendation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: str
    forecast_qty: float
    stock_qty: int
    reorder_qty: float
    confidence: float
    created_at: Optional[datetime] = None


class AlertSettings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone: str = ""
    threshold: Optional[float] = None
    enabled: bool = True


class RecommendationOut(SQLModel):
    item_id: str
    forecast_qty: float
    stock_qty: int
    reorder_qty: float
    confidence: float
    reason: str


class IngestItem(BaseModel):
    date: datetime
    item_id: str = Field(..., validation_alias=AliasChoices("item_id", "item-id"))
    qty: int = Field(..., gt=0)
    price: float = Field(..., ge=0)

    @field_validator("date", mode="before")
    @classmethod
    def _as_utc(cls, value):
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value is not None and getattr(value, "tzinfo", None) is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class StockUpdate(BaseModel):
    item_id: str
    qty: int = Field(..., ge=0)


class AlertSettingsUpdate(BaseModel):
    phone: str = ""
    threshold: Optional[float] = Field(None, ge=0)
    enabled: bool = True


class AlertTarget(BaseModel):
    item_id: Optional[str] = None


def fetch_window_sales(engine: Engine, window_start: datetime) -> list:
    with Session(engine) as session:
        return session.exec(select(Sale).where(Sale.date >= window_start)).all()


def compute_recommendations(sales: list, stocks: dict) -> list:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=FORECAST_WINDOW_DAYS)
    by_item: dict = {}
    for sale in sales:
        if sale.qty <= 0 or not (window_start <= sale.date <= now):
            continue
        by_item.setdefault(sale.item_id, []).append(sale)

    results = []
    for item_id, item_sales in by_item.items():
        stock_qty = int(stocks.get(item_id, 0) or 0)
        total_qty = sum(s.qty for s in item_sales)
        selling_days = len({s.date.date() for s in item_sales})
        daily_avg = total_qty / selling_days if selling_days else 0.0
        forecast_qty = daily_avg * FORECAST_HORIZON_DAYS
        if forecast_qty <= stock_qty * RESTOCK_FRACTION:
            continue
        results.append(
            RecommendationOut(
                item_id=item_id,
                forecast_qty=round(forecast_qty, 2),
                stock_qty=stock_qty,
                reorder_qty=round(max(0.0, forecast_qty - stock_qty), 2),
                confidence=round(min(1.0, selling_days / 14.0), 2),
                reason=f"forecast {forecast_qty:.1f} exceeds stock threshold {stock_qty * RESTOCK_FRACTION:.1f}",
            )
        )
    return sorted(results, key=lambda r: r.forecast_qty, reverse=True)[:5]


def should_send_alert(settings: AlertSettings, forecast_qty: float) -> bool:
    if not settings.enabled:
        return False
    if settings.threshold is None:
        return True
    return forecast_qty >= settings.threshold


def send_sms(recommendation: Optional[RecommendationOut], settings: AlertSettings) -> dict:
    if recommendation is None:
        return {"sent": False, "reason": "no_recommendation"}
    if not should_send_alert(settings, recommendation.forecast_qty):
        return {"sent": False, "reason": "below_threshold"}
    message = (
        f"Local Lens: low stock for {recommendation.item_id}. "
        f"Forecast {recommendation.forecast_qty:.0f} units against stock of {recommendation.stock_qty}. "
        f"Suggested reorder: {recommendation.reorder_qty:.0f}."
    )
    if os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN") and os.environ.get("TWILIO_FROM_NUMBER"):
        from twilio.rest import Client

        twilio_client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
        message = twilio_client.messages.create(
            body=message,
            from_=os.environ["TWILIO_FROM_NUMBER"],
            to=settings.phone,
        )
        return {"sent": True, "provider": "twilio", "sid": message.sid, "item_id": recommendation.item_id, "body": message}
    return {"sent": True, "provider": "mock", "to": settings.phone, "item_id": recommendation.item_id, "body": message}


def recompute_and_store(engine: Engine) -> None:
    window_start = datetime.now(timezone.utc) - timedelta(days=FORECAST_WINDOW_DAYS)
    sales = fetch_window_sales(engine, window_start)
    with Session(engine) as session:
        stocks = {s.item_id: s.qty for s in session.exec(select(Stock)).all()}
    recommendations = compute_recommendations(sales, stocks)
    with Session(engine) as session:
        for existing in session.exec(select(Recommendation)).all():
            session.delete(existing)
        for rec in recommendations:
            session.add(
                Recommendation(
                    item_id=rec.item_id,
                    forecast_qty=rec.forecast_qty,
                    stock_qty=rec.stock_qty,
                    reorder_qty=rec.reorder_qty,
                    confidence=rec.confidence,
                    created_at=datetime.now(timezone.utc),
                )
            )
        session.commit()


async def _edge_tick(engine: Engine, interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        recompute_and_store(engine)


def create_app(database_url: str = "sqlite:///./data.db") -> FastAPI:
    engine = create_engine(
        database_url,
        echo=False,
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
    )
    SQLModel.metadata.create_all(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        interval = float(os.environ.get("EDGE_TICK_SECONDS", "300"))
        task = asyncio.create_task(_edge_tick(engine, interval))
        yield
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    app = FastAPI(lifespan=lifespan)
    app.state.engine = engine

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/ingest", status_code=201)
    def ingest(items: list[IngestItem]):
        with Session(engine) as session:
            for item in items:
                session.add(
                    Sale(
                        date=item.date,
                        item_id=item.item_id,
                        qty=item.qty,
                        price=item.price,
                        synced_at=None,
                    )
                )
            session.commit()
        return {"ingested": len(items)}

    @app.post("/sync")
    def sync():
        with Session(engine) as session:
            pending = session.exec(select(Sale).where(Sale.synced_at == None)).all()  # noqa: E711
            for sale in pending:
                sale.synced_at = datetime.now(timezone.utc)
            session.commit()
        return {"synced": len(pending)}

    @app.put("/stock")
    def set_stock(payload: StockUpdate):
        with Session(engine) as session:
            existing = session.exec(select(Stock).where(Stock.item_id == payload.item_id)).first()
            if existing is None:
                session.add(Stock(item_id=payload.item_id, qty=payload.qty))
            else:
                existing.qty = payload.qty
            session.commit()
        return {"item_id": payload.item_id, "qty": payload.qty}

    @app.get("/recommendations")
    def get_recommendations():
        window_start = datetime.now(timezone.utc) - timedelta(days=FORECAST_WINDOW_DAYS)
        sales = fetch_window_sales(engine, window_start)
        with Session(engine) as session:
            stocks = {s.item_id: s.qty for s in session.exec(select(Stock)).all()}
        return [r.model_dump() for r in compute_recommendations(sales, stocks)]

    @app.get("/settings")
    def get_settings():
        with Session(engine) as session:
            settings_row = session.exec(select(AlertSettings).where(AlertSettings.id == 1)).first()
            if settings_row is None:
                return {"phone": "", "threshold": None, "enabled": True}
            return {"phone": settings_row.phone, "threshold": settings_row.threshold, "enabled": settings_row.enabled}

    @app.put("/settings")
    def update_settings(payload: AlertSettingsUpdate):
        with Session(engine) as session:
            settings_row = session.exec(select(AlertSettings).where(AlertSettings.id == 1)).first()
            if settings_row is None:
                settings_row = AlertSettings(id=1, phone=payload.phone, threshold=payload.threshold, enabled=payload.enabled)
                session.add(settings_row)
            else:
                settings_row.phone = payload.phone
                settings_row.threshold = payload.threshold
                settings_row.enabled = payload.enabled
            session.commit()
        return {"phone": payload.phone, "threshold": payload.threshold, "enabled": payload.enabled}

    @app.post("/alerts")
    def send_alert(target: AlertTarget):
        window_start = datetime.now(timezone.utc) - timedelta(days=FORECAST_WINDOW_DAYS)
        sales = fetch_window_sales(engine, window_start)
        with Session(engine) as session:
            stocks = {s.item_id: s.qty for s in session.exec(select(Stock)).all()}
            settings_row = session.exec(select(AlertSettings).where(AlertSettings.id == 1)).first()
            settings = settings_row if settings_row is not None else AlertSettings(id=1)
            recommendations = compute_recommendations(sales, stocks)
            recommendation = None
            if target.item_id:
                recommendation = next((r for r in recommendations if r.item_id == target.item_id), None)
            elif recommendations:
                recommendation = recommendations[0]
        return send_sms(recommendation, settings)

    app.mount("/", StaticFiles(directory="static", html=True), name="static")

    return app
