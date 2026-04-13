import asyncio
import BAC0


async def main():
    b = BAC0.start(ip="127.0.0.1/24")
    await asyncio.sleep(1)
    try:
        result = b.discover() if hasattr(b, 'discover') else None
        print('discover_result', result)
        print('discoveredDevices', getattr(b, 'discoveredDevices', None))
    finally:
        b.disconnect()


asyncio.run(main())
