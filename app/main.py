from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from app.api.students import router as students_router
from app.api.languages import router as languages_router
from app.api.staff import router as staff_router
from app.api.lessons import router as lessons_router
from app.api.bookings import router as booking_router

from app.core.docs import api_description, tags_metadata

app = FastAPI(
    title="Lingua School API 🎓",
    description=api_description,
    version="1.0.0",
    openapi_tags=tags_metadata
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vk.com",
        "https://mini.apps.vk.com",
        "https://app54520332.vk-apps.com",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students_router)
app.include_router(languages_router)
app.include_router(staff_router)
app.include_router(lessons_router)
app.include_router(booking_router)

# Раздаём Mini App как статику по пути /miniapp
MINIAPP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "miniapp")
if os.path.isdir(MINIAPP_DIR):
    app.mount("/miniapp", StaticFiles(directory=MINIAPP_DIR, html=True), name="miniapp")

    @app.get("/miniapp", include_in_schema=False)
    async def miniapp_root():
        return FileResponse(os.path.join(MINIAPP_DIR, "index.html"))