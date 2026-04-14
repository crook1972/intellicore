from __future__ import annotations

from datetime import datetime
from typing import Any

from pymodbus.client import ModbusTcpClient
from sqlmodel import Session, select

from .models import Device, Point


class ModbusPollingService:
    def __init__(self, host: str, port: int = 502, unit_id: int = 1):
        self.host = host
        self.port = port
        self.unit_id = unit_id

    def poll_holding_registers(self, session: Session, start_address: int = 0, register_count: int = 10) -> dict[str, Any]:
        client = ModbusTcpClient(host=self.host, port=self.port)
        if not client.connect():
            raise RuntimeError(f"Unable to connect to Modbus TCP device at {self.host}:{self.port}")

        try:
            response = client.read_holding_registers(address=start_address, count=register_count, slave=self.unit_id)
            if response.isError():
                raise RuntimeError(f"Modbus poll failed: {response}")

            device = self._upsert_device(session)
            points_synced = self._store_registers(session, device, start_address, list(response.registers))
            session.commit()

            return {
                "device": {"address": device.address, "name": device.name, "protocol": device.protocol},
                "points_synced": points_synced,
            }
        finally:
            client.close()

    def _upsert_device(self, session: Session) -> Device:
        address = f"{self.host}:{self.port}:{self.unit_id}"
        existing = session.exec(select(Device).where(Device.address == address, Device.protocol == "modbus-tcp")).first()
        device = existing or Device(address=address, device_instance=self.unit_id, protocol="modbus-tcp")
        device.name = f"Modbus Device {self.unit_id}"
        device.vendor = None
        device.model_name = "Modbus TCP"
        device.last_seen = datetime.utcnow()
        session.add(device)
        session.flush()
        return device

    def _store_registers(self, session: Session, device: Device, start_address: int, registers: list[int]) -> int:
        synced = 0
        for offset, value in enumerate(registers):
            register_address = start_address + offset
            object_identifier = f"holding-register:{register_address}"
            existing = session.exec(select(Point).where(Point.device_id == device.id, Point.object_identifier == object_identifier)).first()
            point = existing or Point(device_id=device.id, object_identifier=object_identifier)
            point.object_name = f"Holding Register {register_address}"
            point.object_type = "holding-register"
            point.present_value = str(value)
            point.units = "raw"
            point.last_sampled = datetime.utcnow()
            session.add(point)
            synced += 1

        return synced
