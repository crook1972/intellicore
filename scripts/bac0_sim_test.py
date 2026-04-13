import asyncio
import BAC0


async def main():
    sim = BAC0.start(ip="127.0.0.2/24")
    scanner = BAC0.start(ip="127.0.0.1/24")
    await asyncio.sleep(2)
    try:
        iams = await scanner.who_is(address='127.0.0.2', timeout=5)
        print('iams_count', len(iams))
        if iams:
            iam = iams[0]
            print('iam_attrs', [a for a in dir(iam) if not a.startswith('_')][:80])
            print('pduSource', getattr(iam, 'pduSource', None))
            print('iAmDeviceIdentifier', getattr(iam, 'iAmDeviceIdentifier', None))
    finally:
        sim.disconnect()
        scanner.disconnect()


asyncio.run(main())
