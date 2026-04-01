from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import settings
from app.core.database import get_async_session
from app.models.users import Staff, Student
from app.core.security import is_valid_vk_query
from urllib.parse import parse_qsl
from fastapi import Header

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="staff/login")

async def get_current_staff(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session)
) -> Staff:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    query = select(Staff).where(Staff.email == email).options(selectinload(Staff.languages))
    result = await session.execute(query)
    staff_user = result.scalar_one_or_none()
    
    if staff_user is None:
        raise credentials_exception
    if not staff_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return staff_user

async def get_current_active_admin(current_staff: Staff = Depends(get_current_staff)) -> Staff:
    if current_staff.role != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав (только для админов)")
    return current_staff

async def get_current_student(
    x_vk_params: str = Header(..., description="Параметры запуска VK Mini App"),
    session: AsyncSession = Depends(get_async_session)
) -> Student:
    if not is_valid_vk_query(x_vk_params):
        raise HTTPException(status_code=403, detail="Неверная подпись VK")
    params_dict = dict(parse_qsl(x_vk_params))
    vk_id = int(params_dict.get("vk_user_id"))
    query = select(Student).where(Student.vk_id == vk_id)
    result = await session.execute(query)
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=401, detail="Студент не найден. Вызовите /auth первой")
    return student

async def get_optional_current_student(
    x_vk_params: str | None = Header(None, description="Параметры запуска VK Mini App (необязательно)"),
    session: AsyncSession = Depends(get_async_session)
) -> Student | None:
    if not x_vk_params:
        return None
    if not is_valid_vk_query(x_vk_params):
        return None
    params_dict = dict(parse_qsl(x_vk_params))
    vk_id = params_dict.get("vk_user_id")
    if not hasattr(vk_id, 'isdigit') or not str(vk_id).isdigit():
        return None
    query = select(Student).where(Student.vk_id == int(vk_id))
    result = await session.execute(query)
    return result.scalar_one_or_none()
