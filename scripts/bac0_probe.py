import asyncio
import BAC0


async def main():
    b = BAC0.start(ip="127.0.0.1/24")
    app = b.this_application
    print(type(app))
    print([n for n in dir(app) if 'object' in n.lower() or 'add' in n.lower()][:120])
    await asyncio.sleep(1)
    b.disconnect()


asyncio.run(main())
