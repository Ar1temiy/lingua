import asyncio
from datetime import date
from sqlalchemy import select, cast, Date
from app.core.database import async_session_maker
from app.models.education import Lesson

async def main():
    async with async_session_maker() as session:
        query = select(Lesson).where(
            cast(Lesson.start_time, Date) >= date(2026, 4, 2),
            cast(Lesson.start_time, Date) <= date(2026, 4, 2)
        )
        res = await session.execute(query)
        lessons = res.scalars().all()
        print("LESSONS FOUND:", len(lessons))
        for l in lessons:
            print(f"ID: {l.id}, start_time: {l.start_time}")

asyncio.run(main())
