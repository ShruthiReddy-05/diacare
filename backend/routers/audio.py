import os
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional

from database import get_db
from models.audio_asset import AudioAsset
from schemas.audio_asset import AudioAssetResponse

router = APIRouter(prefix="/api/audio-assets", tags=["Audio Assets"])


@router.get("/lookup")
async def lookup_audio_asset(
    questionnaire_id: str = Query(...),
    question_id: str = Query(...),
    language: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AudioAsset).where(
        AudioAsset.questionnaire_id == questionnaire_id,
        AudioAsset.question_id == question_id,
        AudioAsset.language == language,
    ).order_by(AudioAsset.created_at.desc()).limit(1)
    result = await db.execute(stmt)
    asset = result.scalar()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching audio asset")
    return {
        "id": asset.id,
        "fileUrl": f"/api/audio-assets/{asset.id}/file",
        "mimeType": asset.mime_type,
    }


@router.get("/{asset_id}", response_model=AudioAssetResponse)
async def get_audio_asset(asset_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AudioAsset).where(AudioAsset.id == asset_id)
    result = await db.execute(stmt)
    asset = result.scalar()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio asset not found."
        )
    return asset


@router.get("/{asset_id}/file")
async def stream_audio_file(asset_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AudioAsset).where(AudioAsset.id == asset_id)
    result = await db.execute(stmt)
    asset = result.scalar()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio asset not found."
        )
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    rel = asset.file_path
    if rel.startswith("media") or rel.startswith("media\\"):
        rel = rel[6:] if rel.startswith("media\\") else rel[6:]
    abs_path = os.path.join(backend_dir, "media", rel.lstrip("\\/"))
    if not os.path.isfile(abs_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found on disk."
        )
    return FileResponse(abs_path, media_type=asset.mime_type)
