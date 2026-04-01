from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_async_session
from app.models.education import Language
from app.schemas.education import LanguageCreate, LanguageResponse


router = APIRouter(prefix="/languages", tags=["Языки"])


@router.post("/", response_model=LanguageResponse, status_code=status.HTTP_201_CREATED)
async def create_language(
        language: LanguageCreate,
        session: AsyncSession = Depends(get_async_session)
):

    #проверяем нет ли уже такого языка
    query = select(Language).where(Language.code == language.code)
    result = await session.execute(query)
    existing_lang = result.scalar_one_or_none()

    if existing_lang:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Язык с таким кодом уже существует"
        )

    new_language = Language(name=language.name, code=language.code)

    session.add(new_language)
    await session.commit()
    await session.refresh(new_language)

    return new_language


@router.get("/", response_model=List[LanguageResponse])
async def get_languages(session: AsyncSession = Depends(get_async_session)):
    query = select(Language)
    result = await session.execute(query)

    languages = result.scalars().all()

    return languages