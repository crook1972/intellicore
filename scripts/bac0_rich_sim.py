import asyncio

import BAC0
from BAC0.core.devices.local.factory import ObjectFactory, analog_value, binary_value


async def main():
    sim = BAC0.start(ip="127.0.0.2/24")
    await asyncio.sleep(1)
    try:
        ObjectFactory.clear_objects()
        analog_value(name="ZoneTemp", instance=1, presentValue=72.5, properties={"units": "degreesFahrenheit"}).add_objects_to_application(sim)
        analog_value(name="ZoneHumidity", instance=2, presentValue=45.2, properties={"units": "percentRelativeHumidity"}).add_objects_to_application(sim)
        binary_value(name="Occupied", instance=3, presentValue="active").add_objects_to_application(sim)
        print("BACnet rich simulator running at 127.0.0.2/24")
        await asyncio.sleep(300)
    finally:
        sim.disconnect()


asyncio.run(main())
