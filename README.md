# Local Lens AI Analytics

Team beta — spec §3.2 hackathon build.

**One-liner:** Empower rural retailers with low‑cost, offline‑first AI insights that run on their existing POS, using local sensors and adaptive SMS/web alerts.

**Problem:** Small rural stores struggle with inventory waste and missed sales because they lack affordable, reliable analytics that can run offline and adapt to low‑bandwidth conditions.

**Solution:** A lightweight, AI‑driven analytics package that (1) ingests POS sales, (2) supplements with optional local Bluetooth/Wi‑Fi foot‑traffic probes, (3) buffers data on a local edge device for intermittent connectivity, (4) runs privacy‑preserving models on‑device, (5) syncs when online, and (6) delivers actionable recommendations via a minimal web dashboard and configurable SMS alerts, with adaptive thresholds to avoid overload.

**Build scope:** **Local Lens AI Analytics – Day 4‑5 Architecture (§3.1)**  

**Tech‑stack (single repo, single run command)**  
- **Frontend:** static HTML + Tailwind CSS, minimal vanilla JS for chart rendering (Chart.js via CDN).  
- **Backend:** Python 3.11 + FastAPI (single file `app.py`).  
- **Storage:** SQLite file (`data.db`) accessed via SQLModel.  
- **Run command:** `docker compose up` (or `python -m uvicorn app:app --host 0.0.0.0`) – one container, no external services.  

**Three MVP components**  

1. **POS Ingestion Service** – POST `/ingest` accepts a small CSV‑style payload (date, item‑id, qty, price). Data is written to SQLite and appended to an “unsynced” queue.  

2. **Edge‑AI Engine** – A scheduled FastAPI background task runs every 5 min, loads the last 30 days of sales, computes a simple moving‑average forecast and flags items where forecast > current stock × 0.8. Results are stored in a `recommendations` table.  

3. **Dashboard & SMS Trigger** – `/` serves the static page showing a bar chart of “Top 5 items to restock”. A tiny function uses the local Twilio‑sandbox credentials (the *only* external API, mocked with a JSON fixture when network is disabled) to POST an SMS when a recommendation crosses a user‑set threshold.  

**Top 2 Risks**  
- **Offline/low‑bandwidth handling:** background task must not block the API; mitigated by using FastAPI’s async scheduler and local SQLite buffering.  
- **Model oversimplification:** a naïve moving‑average may produce false alerts; mitigated by exposing a “confidence” slider and logging raw forecasts for later refinement.  

**Fallback (out‑of‑scope) scope**  
- Real Bluetooth/Wi‑Fi beacon collector (replace with a static CSV fixture).  
- Multi‑store syncing, cloud dashboards, custom model training, Kubernetes deployment, compliance audits, and any third‑party analytics SDKs.  

*Result:* `git clone … && docker compose up` launches a self‑contained edge analytics node that ingests POS data, runs on‑device forecasts, and surfaces actionable restock recommendations via a single‑page UI and optional SMS alerts.

Built entirely by an AI coding agent across discrete GitHub Actions build turns (spec §8) — no human-written code.
