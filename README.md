# IntelliCore MVP

Lightweight on-site BAS discovery appliance for BACnet/IP-first discovery, with local FastAPI dashboard and SQLite persistence.

## MVP scope
- BACnet/IP network discovery
- best-effort device metadata and object list reads
- latest point value sampling
- local web dashboard
- Raspberry Pi friendly deployment

## Run locally
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.intellicore_backend.main:app --reload
```

Then open `http://127.0.0.1:8000`.

## Environment
- `INTELLICORE_DB_URL` default: `sqlite:///./intellicore.db`
- `INTELLICORE_BACNET_IP` default: `127.0.0.1/24`
- `INTELLICORE_BACNET_POLL_LIMIT` default: `5`

## Raspberry Pi note
Designed to stay lightweight by using FastAPI + Jinja templates and local SQLite. Install into a Python venv and run under systemd or uvicorn directly.
