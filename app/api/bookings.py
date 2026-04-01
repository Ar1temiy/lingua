import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from sqlalchemy.orm import selectinload
from app.core.database import get_async_session
from app.core.dependencies import get_current_staff, get_current_student
from ..models.education import Lesson, Booking, BookingStatusEnum
from app.models.users import Staff, Student
from app.schemas.bookings import BookingCreate, BookingResponse, BookingStatusUpdate, BookingDetailResponse

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

@router.patch("/{booking_id}/status", response_model=BookingResponse)
async def update_booking_status(
    booking_id: uuid.UUID,
    status_update: BookingStatusUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_staff: Staff = Depends(get_current_staff)
):
    query = select(Booking).join(Lesson).where(Booking.id == booking_id)
    result = await session.execute(query)
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    if current_staff.role == "teacher" and booking.lesson.teacher_id != current_staff.id:
        raise HTTPException(status_code=403, detail="Действие запрещено. Это запись не к вам на занятие.")
        
    booking.status = status_update.status
    await session.commit()
    await session.refresh(booking)
    return booking

@router.get("/my", response_model=List[BookingDetailResponse])
async def get_my_bookings(
    session: AsyncSession = Depends(get_async_session),
    current_student: Student = Depends(get_current_student)
):
    query = select(Booking).where(
        Booking.student_id == current_student.id
    ).options(selectinload(Booking.lesson))
    result = await session.execute(query)
    return result.scalars().all()

@router.patch("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_my_booking(
    booking_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_student: Student = Depends(get_current_student)
):
    query = select(Booking).where(Booking.id == booking_id)
    result = await session.execute(query)
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    if booking.student_id != current_student.id:
        raise HTTPException(status_code=403, detail="Это не ваша запись")
        
    booking.status = BookingStatusEnum.cancelled_by_student
    await session.commit()
    await session.refresh(booking)
    return booking