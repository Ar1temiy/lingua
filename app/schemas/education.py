import uuid
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.education import LessonTypeEnum, LessonStatusEnum


#принимаем данные
class LanguageCreate(BaseModel):
    name: str
    code: str

#ответ
class LanguageResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    model_config = ConfigDict(from_attributes=True)


class LessonCreate(BaseModel):
    teacher_id: uuid.UUID | None = None
    language_id: uuid.UUID
    type: LessonTypeEnum
    capacity: int = 1
    start_time: datetime
    end_time: datetime

class LessonResponse(BaseModel):
    id: uuid.UUID
    teacher_id: uuid.UUID
    language_id: uuid.UUID
    type: LessonTypeEnum
    capacity: int
    start_time: datetime
    end_time: datetime
    status: LessonStatusEnum
    teacher_name: str | None = None
    language_name: str | None = None

    model_config = ConfigDict(from_attributes=True)

class LessonStudentResponse(LessonResponse):
    available_slots: int
    is_booked_by_me: bool

class LessonStatusUpdate(BaseModel):
    status: LessonStatusEnum