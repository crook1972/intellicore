from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from .bacnet import BacnetDiscoveryService
from .config import settings
from .database import get_session, init_db
from .models import Device, Point

app = FastAPI(title=settings.app_name)
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_session)):
    devices = session.exec(select(Device).order_by(Device.last_seen.desc())).all()
    points = session.exec(select(Point).order_by(Point.last_sampled.desc())).all()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "devices": devices,
            "points": points,
            "config": settings,
            "message": None,
        },
    )


@app.post("/scan", response_class=HTMLResponse)
async def run_scan(
    request: Request,
    target_ip: str = Form(default=""),
    session: Session = Depends(get_session),
):
    service = BacnetDiscoveryService(ip=settings.bacnet_ip, poll_limit=settings.bacnet_poll_limit)
    try:
        result = await service.scan(session, target=target_ip or None)
        message = f"Scan complete, found {result['devices_found']} BACnet devices."
    except Exception as exc:
        message = f"Scan failed: {exc}"

    devices = session.exec(select(Device).order_by(Device.last_seen.desc())).all()
    points = session.exec(select(Point).order_by(Point.last_sampled.desc())).all()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "devices": devices,
            "points": points,
            "config": settings,
            "message": message,
        },
    )


@app.get("/api/devices")
def api_devices(session: Session = Depends(get_session)):
    return session.exec(select(Device).order_by(Device.last_seen.desc())).all()


@app.get("/api/points")
def api_points(session: Session = Depends(get_session)):
    return session.exec(select(Point).order_by(Point.last_sampled.desc())).all()


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
