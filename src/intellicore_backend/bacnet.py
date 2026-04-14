from __future__ import annotations

from datetime import datetime
from typing import Any

import BAC0
from sqlmodel import Session, select

from .models import Device, Point


STANDARD_VALUE_OBJECTS = {
    "analogInput",
    "analog-input",
    "analogOutput",
    "analog-output",
    "analogValue",
    "analog-value",
    "binaryInput",
    "binary-input",
    "binaryOutput",
    "binary-output",
    "binaryValue",
    "binary-value",
    "multiStateInput",
    "multi-state-input",
    "multiStateOutput",
    "multi-state-output",
    "multiStateValue",
    "multi-state-value",
}


class BacnetDiscoveryService:
    def __init__(self, ip: str, poll_limit: int = 5):
        self.ip = ip
        self.poll_limit = poll_limit

    async def scan(self, session: Session, target: str | None = None) -> dict[str, Any]:
        bacnet = BAC0.start(ip=self.ip)
        discovered = []
        points_synced = 0
        try:
            iams = await bacnet.who_is(address=target, timeout=5) if target else await bacnet.who_is(timeout=5)
            for iam in iams or []:
                device_result = await self._normalize_and_store_device(bacnet, session, iam)
                points_synced += int(device_result.pop("points_synced", 0))
                discovered.append(device_result)
            session.commit()
        finally:
            try:
                bacnet.disconnect()
            except Exception:
                pass

        return {"devices_found": len(discovered), "points_synced": points_synced, "devices": discovered}

    async def _normalize_and_store_device(self, bacnet: Any, session: Session, iam: Any) -> dict[str, Any]:
        address = str(getattr(iam, "pduSource", "unknown"))
        raw_identifier = str(getattr(iam, "iAmDeviceIdentifier", "device,0"))
        instance = int(raw_identifier.split(",")[-1]) if "," in raw_identifier else None

        name = await self._safe_read(bacnet, f"{address} device {instance} objectName") or f"Device {instance}"
        vendor = await self._safe_read(bacnet, f"{address} device {instance} vendorName")
        model_name = await self._safe_read(bacnet, f"{address} device {instance} modelName")

        matches = session.exec(
            select(Device).where(Device.address == address, Device.protocol == "bacnet").order_by(Device.last_seen.desc())
        ).all()
        existing = matches[0] if matches else None
        device = existing or Device(address=address, device_instance=instance)
        device.name = str(name)
        device.vendor = str(vendor) if vendor is not None else None
        device.model_name = str(model_name) if model_name is not None else None
        device.last_seen = datetime.utcnow()
        session.add(device)
        session.flush()

        for duplicate in matches[1:]:
            duplicate_points = session.exec(select(Point).where(Point.device_id == duplicate.id)).all()
            for point in duplicate_points:
                point.device_id = device.id
                session.add(point)
            session.delete(duplicate)

        points_synced = await self._sync_points(bacnet, session, device)

        return {
            "device_instance": instance,
            "address": address,
            "name": device.name,
            "vendor": device.vendor,
            "model_name": device.model_name,
            "points_synced": points_synced,
        }

    async def _sync_points(self, bacnet: Any, session: Session, device: Device) -> int:
        if device.device_instance is None:
            return 0

        object_list = await self._safe_read(bacnet, f"{device.address} device {device.device_instance} objectList") or []
        if not isinstance(object_list, (list, tuple)):
            return 0

        value_objects = [obj for obj in object_list if self._object_type(obj) in STANDARD_VALUE_OBJECTS][: self.poll_limit]
        synced = 0
        for obj in value_objects:
            object_type = self._object_type(obj)
            object_instance = self._object_instance(obj)
            object_identifier = f"{object_type}:{object_instance}"
            object_name = await self._safe_read(bacnet, f"{device.address} {object_type} {object_instance} objectName") or object_identifier
            present_value = await self._safe_read(bacnet, f"{device.address} {object_type} {object_instance} presentValue")
            units = await self._safe_read(bacnet, f"{device.address} {object_type} {object_instance} units")

            existing = session.exec(select(Point).where(Point.device_id == device.id, Point.object_identifier == object_identifier)).first()
            point = existing or Point(device_id=device.id, object_identifier=object_identifier)
            point.object_name = str(object_name)
            point.object_type = object_type
            point.present_value = None if present_value is None else str(present_value)
            point.units = None if units is None else str(units)
            point.last_sampled = datetime.utcnow()
            session.add(point)
            synced += 1

        return synced

    @staticmethod
    async def _safe_read(bacnet: Any, query: str) -> Any:
        try:
            return await bacnet.read(query)
        except Exception:
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
