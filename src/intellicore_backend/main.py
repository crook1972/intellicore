from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from .bacnet import BacnetDiscoveryService
from .config import settings
from .database import get_session, init_db
from .modbus import ModbusPollingService
from .models import Device, Point

app = FastAPI(title=settings.app_name)
templates = Jinja2Templates(directory="templates")


def render_dashboard(request: Request, session: Session, message: str | None = None, message_level: str = "info"):
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
            "message_level": message_level,
        },
    )


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_session)):
    return render_dashboard(request, session)


@app.post("/scan", response_class=HTMLResponse)
async def run_scan(
    request: Request,
    target_ip: str = Form(default=""),
    session: Session = Depends(get_session),
):
    service = BacnetDiscoveryService(ip=settings.bacnet_ip, poll_limit=settings.bacnet_poll_limit)
    try:
        result = await service.scan(session, target=target_ip or None)
        message = f"BACnet scan complete, found {result['devices_found']} devices and synced {result['points_synced']} points."
        level = "success"
    except Exception as exc:
        message = f"Scan failed: {exc}"
        level = "error"

    return render_dashboard(request, session, message=message, message_level=level)


@app.post("/modbus/poll", response_class=HTMLResponse)
def poll_modbus(
    request: Request,
    host: str = Form(default=""),
    port: int = Form(default=502),
    unit_id: int = Form(default=1),
    start_address: int = Form(default=0),
    register_count: int = Form(default=10),
    session: Session = Depends(get_session),
):
    service = ModbusPollingService(host=host or settings.modbus_host, port=port, unit_id=unit_id)
    try:
        result = service.poll_holding_registers(session, start_address=start_address, register_count=register_count)
        message = f"Modbus poll complete for {result['device']['address']}, synced {result['points_synced']} registers."
        level = "success"
    except Exception as exc:
        message = f"Modbus poll failed: {exc}"
        level = "error"

    return render_dashboard(request, session, message=message, message_level=level)


@app.get("/points/live", response_class=HTMLResponse)
def live_points(request: Request, session: Session = Depends(get_session)):
    points = session.exec(select(Point).order_by(Point.last_sampled.desc())).all()
    return templates.TemplateResponse(
        request,
        "live_points.html",
        {
            "points": points,
            "config": settings,
        },
    )


@app.get("/devices/{device_id}", response_class=HTMLResponse)
def device_detail(device_id: int, request: Request, session: Session = Depends(get_session)):
    device = session.get(Device, device_id)
    points = session.exec(select(Point).where(Point.device_id == device_id).order_by(Point.last_sampled.desc())).all()
    return templates.TemplateResponse(request, "device.html", {"device": device, "points": points})


@app.get("/api/devices")
def api_devices(session: Session = Depends(get_session)):
    return session.exec(select(Device).order_by(Device.last_seen.desc())).all()


@app.get("/api/points")
def api_points(session: Session = Depends(get_session)):
    return session.exec(select(Point).order_by(Point.last_sampled.desc())).all()


@app.get("/api/devices/{device_id}/points")
def api_device_points(device_id: int, session: Session = Depends(get_session)):
    return session.exec(select(Point).where(Point.device_id == device_id).order_by(Point.last_sampled.desc())).all()


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
