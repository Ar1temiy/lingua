import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.core.database import get_async_session
from app.models.education import Lesson, LessonStatusEnum
from app.models.users import Staff
from app.schemas.education import LessonCreate, LessonResponse
from datetime import date

router = APIRouter(prefix="/lessons", tags=["Расписание (Занятия)"])

@router.post("/", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    lesson: LessonCreate,
    session: AsyncSession = Depends(get_async_session)
):
    if lesson.start_time >= lesson.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Время окончания занятия должно быть позже времени начала"
        )


    teacher_query = select(Staff).where(Staff.id == lesson.teacher_id).options(selectinload(Staff.languages))
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
        teacher_id=lesson.teacher_id,
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
@router.get("/", response_model=List[LessonResponse])
async def get_lessons(
        teacher_id: Optional[uuid.UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        session: AsyncSession = Depends(get_async_session)
):
    query = select(Lesson).where(Lesson.status != LessonStatusEnum.cancelled)

    if teacher_id:
        query = query.where(Lesson.teacher_id == teacher_id)
    if date_from:
        query = query.where(Lesson.start_time >= date_from)
    if date_to:
        query = query.where(Lesson.start_time <= date_to)

    query = query.order_by(Lesson.start_time)
    result = await session.execute(query)
    return result.scalars().all()