from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from sqlalchemy.orm import selectinload
from app.models.education import Language
from app.core.database import get_async_session
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.dependencies import get_current_staff, get_current_active_admin
from app.models.users import Staff
from app.schemas.users import StaffCreate, StaffResponse, Token
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/staff", tags=["Персонал (Учителя и Админы)"])


@router.post("/", summary="Создать профиль сотрудника (Админ)", description="Регистрация нового преподавателя или администратора. Эта ручка доступна только пользователям с ролью `admin`.", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
        staff: StaffCreate,
        session: AsyncSession = Depends(get_async_session)
):

    #Проверяем, не занят ли email
    query = select(Staff).where(Staff.email == staff.email).options(selectinload(Staff.languages))
    result = await session.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сотрудник с таким email уже существует"
        )

    #хешируем пароль
    hashed_password = get_password_hash(staff.password)

    new_staff = Staff(
        email=staff.email,
        hashed_password=hashed_password,
        first_name=staff.first_name,
        last_name=staff.last_name,
        role=staff.role
    )

    session.add(new_staff)
    await session.commit()
    #чтобы не было ошибки LazyLoad
    query = select(Staff).where(Staff.id == new_staff.id).options(selectinload(Staff.languages))
    result = await session.execute(query)
    new_staff = result.scalar_one()

    return new_staff


@router.get("/", summary="Список преподавателей", description="Возвращает публичный список всех преподавателей с подгруженным массивом языков, которые они преподают. Используется фронтендом для выпадающих списков.", response_model=List[StaffResponse])
async def get_all_staff(session: AsyncSession = Depends(get_async_session)):
    query = select(Staff).options(selectinload(Staff.languages))
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/{staff_id}/languages/{language_id}", summary="Привязать язык к преподавателю (Админ)", description="Добавляет специализацию (язык) для конкретного преподавателя.", response_model=StaffResponse)
async def assign_language_to_teacher(
    staff_id: uuid.UUID,
    language_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    #Ищем преподавателя подгружаем его языки
    query = select(Staff).where(Staff.id == staff_id).options(selectinload(Staff.languages))
    result = await session.execute(query)
    teacher = result.scalar_one_or_none()

    if not teacher:
        raise HTTPException(status_code=404, detail="Преподаватель не найден")


    #ищем язык
    language_query = select(Language).where(Language.id == language_id)
    language_res = await session.execute(language_query)
    language = language_res.scalar_one_or_none()

    if not language:
        raise HTTPException(status_code=404, detail="Язык не найден")

    if language in teacher.languages:
        raise HTTPException(status_code=400, detail="Этот язык уже назначен данному преподавателю")

    #Добавляем язык в список
    teacher.languages.append(language)

    await session.commit()
    await session.refresh(teacher)

    return teacher

@router.post("/login", summary="Авторизация персонала (Вход)", description="Классический вход по `email` и `password`. Возвращает JWT токен, который нужно передавать в заголовке `Authorization: Bearer <токен>`.", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session)
):
    query = select(Staff).where(Staff.email == form_data.username)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", summary="Мой профиль (Персонал)", description="Получить данные текущего авторизованного сотрудника (себя).", response_model=StaffResponse)
async def read_staff_me(
    current_staff: Staff = Depends(get_current_staff)
):
    return current_staff