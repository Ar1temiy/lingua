from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.students import router as students_router
from app.api.languages import router as languages_router
from app.api.staff import router as staff_router
from app.api.lessons import router as lessons_router
from app.api.bookings import router as booking_router

app = FastAPI(
    title="Lingua School API",
    description="Бэкенд для VK Mini App языковой школы",
    version="1.0.0"
)

#разрешаем все, в проде поменяем на вк домены
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(students_router)
app.include_router(languages_router)
app.include_router(staff_router)
app.include_router(lessons_router)
app.include_router(booking_router)