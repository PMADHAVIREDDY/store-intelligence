import asyncio
import aiosqlite

async def add_conversions():
    async with aiosqlite.connect('data/store_intel.db') as db:
        await db.execute(
            """UPDATE sessions SET is_converted=1 
               WHERE visitor_id IN (
               'VIS_000001','VIS_000002','VIS_000003',
               'VIS_000005','VIS_000008','VIS_000010',
               'VIS_000012','VIS_000015')"""
        )
        await db.commit()
        cursor = await db.execute("SELECT COUNT(*) FROM sessions WHERE is_converted=1")
        row = await cursor.fetchone()
        print(f'Converted sessions: {row[0]}')
        cursor = await db.execute("SELECT COUNT(*) FROM sessions")
        row = await cursor.fetchone()
        print(f'Total sessions: {row[0]}')

asyncio.run(add_conversions())
