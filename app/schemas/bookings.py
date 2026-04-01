import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.education import BookingStatusEnum
from app.schemas.education import LessonResponse
from app.schemas.users import StaffResponse

class BookingCreate(BaseModel):
    lesson_id: uuid.UUID
    student_id: uuid.UUID #потом убрать, так как айди берется из вк

class BookingResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    lesson_id: uuid.UUID
    status: BookingStatusEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)




class BookingDetailResponse(BaseModel):
    id: uuid.UUID
    status: BookingStatusEnum
    created_at: datetime
    # Магия Pydantic: мы вкладываем одну схему в другую
    lesson: LessonResponse

    model_config = ConfigDict(from_attributes=True)