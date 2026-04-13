from __future__ import annotations

from datetime import datetime
from typing import Any

try:
    import BAC0  # type: ignore
except Exception:  # pragma: no cover
    BAC0 = None

from sqlmodel import Session, select

from .models import Device, Point


STANDARD_VALUE_OBJECTS = {
    "analogInput",
    "analogOutput",
    "analogValue",
    "binaryInput",
    "binaryOutput",
    "binaryValue",
    "multiStateInput",
    "multiStateOutput",
    "multiStateValue",
}


class BacnetDiscoveryService:
    def __init__(self, ip: str, poll_limit: int = 5):
        self.ip = ip
        self.poll_limit = poll_limit

    def scan(self, session: Session) -> dict[str, Any]:
        if BAC0 is None:
            raise RuntimeError("BAC0 is not installed. Install requirements first.")

        bacnet = BAC0.lite(ip=self.ip)
        discovered = []
        try:
            devices = bacnet.discover() or []
            for raw in devices:
                discovered.append(self._normalize_and_store_device(bacnet, session, raw))
            session.commit()
        finally:
            try:
                bacnet.disconnect()
            except Exception:
                pass

        return {"devices_found": len(discovered), "devices": discovered}

    def _normalize_and_store_device(self, bacnet: Any, session: Session, raw: Any) -> dict[str, Any]:
        address = self._extract_address(raw)
        instance = self._extract_instance(raw)
        name = self._safe_read(bacnet, f"{address} device {instance} objectName") or f"Device {instance}"
        vendor = self._safe_read(bacnet, f"{address} device {instance} vendorName")
        model_name = self._safe_read(bacnet, f"{address} device {instance} modelName")

        existing = session.exec(select(Device).where(Device.address == address, Device.device_instance == instance)).first()
        device = existing or Device(address=address, device_instance=instance)
        device.name = str(name)
        device.vendor = str(vendor) if vendor is not None else None
        device.model_name = str(model_name) if model_name is not None else None
        device.last_seen = datetime.utcnow()
        session.add(device)
        session.flush()

        self._sync_points(bacnet, session, device)

        return {
            "device_instance": instance,
            "address": address,
            "name": device.name,
            "vendor": device.vendor,
            "model_name": device.model_name,
        }

    def _sync_points(self, bacnet: Any, session: Session, device: Device) -> None:
        if device.device_instance is None:
            return

        object_list = self._safe_read(bacnet, f"{device.address} device {device.device_instance} objectList") or []
        if not isinstance(object_list, (list, tuple)):
            return

        value_objects = [obj for obj in object_list if self._object_type(obj) in STANDARD_VALUE_OBJECTS][: self.poll_limit]
        for obj in value_objects:
            object_type = self._object_type(obj)
            object_instance = self._object_instance(obj)
            object_identifier = f"{object_type}:{object_instance}"
            object_name = self._safe_read(bacnet, f"{device.address} {object_type} {object_instance} objectName") or object_identifier
            present_value = self._safe_read(bacnet, f"{device.address} {object_type} {object_instance} presentValue")
            units = self._safe_read(bacnet, f"{device.address} {object_type} {object_instance} units")

            existing = session.exec(select(Point).where(Point.device_id == device.id, Point.object_identifier == object_identifier)).first()
            point = existing or Point(device_id=device.id, object_identifier=object_identifier)
            point.object_name = str(object_name)
            point.object_type = object_type
            point.present_value = None if present_value is None else str(present_value)
            point.units = None if units is None else str(units)
            point.last_sampled = datetime.utcnow()
            session.add(point)

    @staticmethod
    def _safe_read(bacnet: Any, query: str) -> Any:
        try:
            return bacnet.read(query)
        except Exception:
            return None

    @staticmethod
    def _extract_address(raw: Any) -> str:
        if isinstance(raw, dict):
            return str(raw.get("address") or raw.get("addr") or "unknown")
        if isinstance(raw, (list, tuple)) and raw:
            return str(raw[0])
        return str(raw)

    @staticmethod
    def _extract_instance(raw: Any) -> int | None:
        if isinstance(raw, dict):
            value = raw.get("device_instance") or raw.get("instance") or raw.get("device_id")
            return int(value) if value is not None else None
        if isinstance(raw, (list, tuple)) and len(raw) > 1:
            try:
                return int(raw[1])
            except Exception:
                return None
        return None

    @staticmethod
    def _object_type(obj: Any) -> str:
        if isinstance(obj, (list, tuple)) and len(obj) >= 1:
            return str(obj[0])
        text = str(obj)
        return text.split(",")[0].strip("() '")

    @staticmethod
    def _object_instance(obj: Any) -> str:
        if isinstance(obj, (list, tuple)) and len(obj) >= 2:
            return str(obj[1])
        text = str(obj)
        parts = text.split(",")
        return parts[1].strip("() '") if len(parts) > 1 else "0"
