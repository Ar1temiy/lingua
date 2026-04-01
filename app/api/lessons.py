import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.core.database import get_async_session
from app.core.dependencies import get_current_staff, get_optional_current_student
from app.models.education import Lesson, LessonStatusEnum, Booking
from app.models.users import Staff, Student
from app.schemas.education import LessonCreate, LessonResponse, LessonStatusUpdate, LessonStudentResponse
from app.schemas.users import StudentResponse
from datetime import date

router = APIRouter(prefix="/lessons", tags=["Расписание (Занятия)"])

@router.post("/", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    lesson: LessonCreate,
    session: AsyncSession = Depends(get_async_session),
    current_staff: Staff = Depends(get_current_staff)
):
    if lesson.start_time >= lesson.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Время окончания занятия должно быть позже времени начала"
        )

    target_teacher_id = lesson.teacher_id or current_staff.id
    if current_staff.role == "teacher" and target_teacher_id != current_staff.id:
        raise HTTPException(status_code=403, detail="Учитель может создавать занятия только для себя")

    teacher_query = select(Staff).where(Staff.id == target_teacher_id).options(selectinload(Staff.languages))
    teacher_res = await session.execute(teacher_query)
    teacher = teacher_res.scalar_one_or_none()


    if not teacher or teacher.role != "teacher":
        raise HTTPException(status_code=404, detail="Преподаватель не найден")


    teacher_language_ids = [lang.id for lang in teacher.languages]
    if lesson.language_id not in teacher_language_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот преподаватель не ведет выбранный язык"
        )


    overlap_query = select(Lesson).where(
        and_(
            Lesson.teacher_id == lesson.teacher_id,
            Lesson.status != LessonStatusEnum.cancelled,
            Lesson.start_time < lesson.end_time,
            Lesson.end_time > lesson.start_time
        )
    )
    overlap_res = await session.execute(overlap_query)
    if overlap_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У преподавателя уже есть занятие в это время (накладка в расписании)"
        )

    new_lesson = Lesson(
        teacher_id=target_teacher_id,
        language_id=lesson.language_id,
        type=lesson.type,
        capacity=lesson.capacity,
        start_time=lesson.start_time,
        end_time=lesson.end_time,
        status=LessonStatusEnum.scheduled
    )

    session.add(new_lesson)
    await session.commit()
    await session.refresh(new_lesson)

    return new_lesson

#получаем все занятия
@router.get("/", response_model=List[LessonStudentResponse])
async def get_lessons(
        teacher_id: Optional[uuid.UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        session: AsyncSession = Depends(get_async_session),
        current_student: Optional[Student] = Depends(get_optional_current_student)
):
    query = select(Lesson).where(Lesson.status != LessonStatusEnum.cancelled)

    if teacher_id:
        query = query.where(Lesson.teacher_id == teacher_id)
    if date_from:
        query = query.where(Lesson.start_time >= date_from)
    if date_to:
        query = query.where(Lesson.start_time <= date_to)

    query = query.order_by(Lesson.start_time).options(selectinload(Lesson.bookings))
    result = await session.execute(query)
    lessons = result.scalars().all()
    
    response = []
    for lesson in lessons:
        active_bookings = [b for b in lesson.bookings if b.status == "active"]
        is_booked = False
        if current_student:
             is_booked = any(b.student_id == current_student.id for b in active_bookings)
             
        available_slots = lesson.capacity - len(active_bookings)
        
        lesson_dict = lesson.__dict__.copy()
        lesson_dict["available_slots"] = available_slots
        lesson_dict["is_booked_by_me"] = is_booked
        response.append(LessonStudentResponse(**lesson_dict))
        
    return response

@router.get("/{lesson_id}/students", response_model=List[StudentResponse])
async def get_lesson_students(
    lesson_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_staff: Staff = Depends(get_current_staff)
):
    query = select(Lesson).where(Lesson.id == lesson_id)
    result = await session.execute(query)
    lesson = result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Занятие не найдено")
    if current_staff.role == "teacher" and lesson.teacher_id != current_staff.id:
        raise HTTPException(status_code=403, detail="Нет доступа к чужому занятию")

    student_query = select(Student).join(Booking).where(
        Booking.lesson_id == lesson_id,
        Booking.status == "active"
    )
    res = await session.execute(student_query)
    return res.scalars().all()

@router.patch("/{lesson_id}/status", response_model=LessonResponse)
async def update_lesson_status(
    lesson_id: uuid.UUID,
    status_update: LessonStatusUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_staff: Staff = Depends(get_current_staff)
):
    query = select(Lesson).where(Lesson.id == lesson_id)
    result = await session.execute(query)
    lesson = result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Занятие не найдено")
    if current_staff.role == "teacher" and lesson.teacher_id != current_staff.id:
        raise HTTPException(status_code=403, detail="Нет доступа к чужому занятию")

    lesson.status = status_update.status
    await session.commit()
    await session.refresh(lesson)
    return lesson