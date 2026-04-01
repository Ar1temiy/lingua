import uuid
from pydantic import BaseModel
from app.models.users import RoleEnum
from .education import LanguageResponse

#что присылает вк на входе
class UserVKAuth(BaseModel):
    vk_launch_params: str
    # если захочет обновить имя
    first_name: str | None
    last_name: str | None

#что бекенд отдаст
class StudentResponse(BaseModel):
    id: uuid.UUID
    vk_id: int
    first_name: str | None
    last_name: str | None
    allow_messages: bool

    model_config = {"from_attributes": True}


#Схема для СОЗДАНИЯ сотрудника
class StaffCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    role: RoleEnum

#Схема для ОТВЕТА
class StaffResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: RoleEnum
    is_active: bool

    languages: list[LanguageResponse] = []
    model_config = {"from_attributes": True}