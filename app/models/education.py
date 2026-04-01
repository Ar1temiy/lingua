import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Table, Column, UniqueConstraint, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base

teacher_languages = Table(
    "teacher_languages",
    Base.metadata,
    Column("teacher_id", UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), primary_key=True),
    Column("language_id", UUID(as_uuid=True), ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True)
)

class LessonTypeEnum(str, enum.Enum):
    individual = "individual"
    group = "group"

class LessonStatusEnum(str, enum.Enum):
    scheduled = "scheduled"
    cancelled = "cancelled"
    completed = "completed"

class BookingStatusEnum(str, enum.Enum):
    active = "active"
    cancelled_by_student = "cancelled_by_student"
    cancelled_by_school = "cancelled_by_school"

class Language(Base):
    __tablename__ = "languages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    code: Mapped[str] = mapped_column(String, unique=True)

    teachers: Mapped[list["Staff"]] = relationship("Staff", secondary=teacher_languages, back_populates="languages")
    lessons: Mapped[list["Lesson"]] = relationship("Lesson", back_populates="language")

class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("languages.id", ondelete="RESTRICT"))
    type: Mapped[LessonTypeEnum] = mapped_column(Enum(LessonTypeEnum))
    capacity: Mapped[int] = mapped_column(default=1)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[LessonStatusEnum] = mapped_column(Enum(LessonStatusEnum), default=LessonStatusEnum.scheduled)

    teacher: Mapped["Staff"] = relationship("Staff", back_populates="lessons")
    language: Mapped["Language"] = relationship("Language", back_populates="lessons")
    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="lesson", cascade="all, delete-orphan")

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    lesson_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"))
    status: Mapped[BookingStatusEnum] = mapped_column(Enum(BookingStatusEnum), default=BookingStatusEnum.active)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint('student_id', 'lesson_id', name='uix_student_lesson'),
    )

    student: Mapped["Student"] = relationship("Student", back_populates="bookings")
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="bookings")