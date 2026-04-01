from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from urllib.parse import parse_qsl

from app.core.database import get_async_session
from app.core.security import is_valid_vk_query
from app.models.users import Student
from app.schemas.users import UserVKAuth, StudentResponse

router = APIRouter(prefix="/students", tags=["Студенты (VK)"])

@router.post("/auth", summary="Авторизация через VK Mini App", description="Авторизует студента по строке запуска VK (`vk_launch_params`). Создает профиль при первом входе, обновляет имя при последующих входах.", response_model=StudentResponse)
async def authenticate_vk_student( #проверка подписи вк
        auth_data: UserVKAuth,
        session: AsyncSession = Depends(get_async_session)):
    if not is_valid_vk_query(auth_data.vk_launch_params):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Неверная подпись VK"
        )

    params_dict = dict(parse_qsl(auth_data.vk_launch_params)) #достаем вк айди
    vk_id = int(params_dict.get("vk_user_id"))

    #идем в базу данных и ищем студента с таким id
    query = select(Student).where(Student.vk_id == vk_id)
    result = await session.execute(query)
    student = result.scalar_one_or_none()  #Student или None

    # если студента нет в базе создаем его
    if student is None:
        student = Student(
            vk_id=vk_id,
            first_name=auth_data.first_name or "Ученик",
            last_name=auth_data.last_name or ""
        )
        session.add(student)
    else:
        # обновляем имя если оно пришло с фронта
        if auth_data.first_name:
            student.first_name = auth_data.first_name
        if auth_data.last_name is not None:
            student.last_name = auth_data.last_name

    await session.commit()  # Сохраняем/обновляем в базе
    await session.refresh(student)

    # возвращаем профиль студента фронтенду
    return student