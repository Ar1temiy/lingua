import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_async_session
from app.models.education import Lesson, Booking, BookingStatusEnum
from app.schemas.bookings import BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["Записи на занятия"])

@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking: BookingCreate,
    session: AsyncSession = Depends(get_async_session)
):

    lesson_query = select(Lesson).where(Lesson.id == booking.lesson_id)
    result = await session.execute(lesson_query)
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Занятие не найдено")


    count_query = select(func.count(Booking.id)).where(
        Booking.lesson_id == lesson.id,
        Booking.status == BookingStatusEnum.active
    )
    count_result = await session.execute(count_query)
    current_bookings_count = count_result.scalar()

    if current_bookings_count >= lesson.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Места на это занятие закончились"
        )

    # Создаем запись
    new_booking = Booking(
        student_id=booking.student_id,
        lesson_id=booking.lesson_id,
        status=BookingStatusEnum.active
    )

    try:
        session.add(new_booking)
        await session.commit()
        await session.refresh(new_booking)
        return new_booking
    except Exception:
        # Здесь сработает UniqueConstraint, если студент нажал кнопку дважды
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже записаны на это занятие"
        )