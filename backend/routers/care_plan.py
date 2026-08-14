import base64
import hashlib
import io
import json
import os
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from database import get_db
from models.baseline_profile import BaselineProfile
from models.module_outcome import ModuleOutcome
from models.care_plan import CarePlan
from models.temporary_audio import TemporaryAudio
from schemas.care_plan import CarePlanResponse
from services.care_plan_generator import generate_care_plan
from routers.conversation import build_user_answers, _baseline_to_dict
from config import settings
from utils import ist_now

router = APIRouter(prefix="/api/care-plan", tags=["Care Plan"])
temp_audio_router = APIRouter(prefix="/api/temporary-audio", tags=["Temporary Audio"])


@router.post("/generate", response_model=CarePlanResponse, status_code=status.HTTP_201_CREATED)
async def generate(user_id: str, db: AsyncSession = Depends(get_db)):
    baseline = (await db.execute(select(BaselineProfile).where(BaselineProfile.user_id == user_id))).scalar()
    if not baseline:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Baseline assessment (A + B1-B3) has not been completed yet.")

    outcomes = (await db.execute(select(ModuleOutcome).where(ModuleOutcome.user_id == user_id))).scalars().all()
    module_outputs = {o.module_id: o.output_json for o in outcomes}

    answers, _, _ = await build_user_answers(user_id, db)
    baseline_dict = _baseline_to_dict(baseline)

    plan_snapshot, traceability = generate_care_plan(answers, baseline_dict, module_outputs)

    care_plan = CarePlan(
        user_id=user_id,
        risk_tier=baseline.overall_risk_tier,
        plan_snapshot=plan_snapshot,
        traceability=traceability,
    )
    db.add(care_plan)
    await db.commit()
    await db.refresh(care_plan)
    return care_plan


@router.get("/{care_plan_id}", response_model=CarePlanResponse)
async def get_care_plan(care_plan_id: str, db: AsyncSession = Depends(get_db)):
    care_plan = (await db.execute(select(CarePlan).where(CarePlan.id == care_plan_id))).scalar()
    if not care_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Care plan not found.")
    return care_plan


@router.get("/user/{user_id}/latest", response_model=CarePlanResponse)
async def get_latest_care_plan(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CarePlan).where(CarePlan.user_id == user_id).order_by(desc(CarePlan.created_at)).limit(1)
    care_plan = (await db.execute(stmt)).scalar()
    if not care_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No care plan found for this user.")
    return care_plan


# ── Care Plan TTS Cache ─────────────────────────────────────────────────────
# The LLM (Sarvam) only ever speaks text already produced by the deterministic
# generator above -- it never drafts or edits any of the words.

MAX_TTS_ATTEMPTS = 3
TEMP_AUDIO_DIR = Path(__file__).resolve().parent.parent / "temp_audio_cache"
TTS_CACHE_TTL_HOURS = 48
SARVAM_TRANSLATE_URL = f"{settings.SARVAM_BASE_URL}/translate"


class TtsResponse(BaseModel):
    asset_id: str


class TtsRequest(BaseModel):
    language: str = "en-IN"


async def _translate_text(text: str, target: str) -> str:
    if not text or not text.strip() or not settings.SARVAM_API_KEY or not target.startswith("ta"):
        return text
    headers = {"API-Subscription-Key": settings.SARVAM_API_KEY}
    payload = {"input": text, "source_language_code": "en-IN", "target_language_code": target, "model": "mayura:v1"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(SARVAM_TRANSLATE_URL, json=payload, headers=headers)
        if resp.status_code == 200:
            return resp.json().get("translated_text", text)
    except Exception:
        pass
    return text


def _care_plan_to_tts_text(snapshot: dict) -> str:
    """Build a spoken summary purely from the already-generated plan text --
    no new wording is ever introduced here."""
    lines = []

    clinical = snapshot.get("clinical_status", {})
    if clinical.get("note"):
        lines.append(clinical["note"])

    for goal in snapshot.get("dietary_goals", {}).get("goals", []):
        if goal.get("text_en"):
            lines.append(goal["text_en"])

    activity = snapshot.get("activity_plan", {})
    if activity.get("weekly_target"):
        lines.append(activity["weekly_target"])
    for precaution in activity.get("foot_precautions", []) or []:
        lines.append(precaution)
    if activity.get("glucose_check_note"):
        lines.append(activity["glucose_check_note"])

    sleep_stress = snapshot.get("sleep_and_stress", {})
    if sleep_stress.get("coping_strategy"):
        lines.append(sleep_stress["coping_strategy"])

    medicines = snapshot.get("medicines", {})
    if medicines.get("adherence_boilerplate"):
        lines.append(medicines["adherence_boilerplate"])
    if medicines.get("herbal_note"):
        lines.append(medicines["herbal_note"])

    hypo = snapshot.get("conditional_hypo_protocol")
    if hypo and hypo.get("protocol_text_en"):
        lines.append(hypo["protocol_text_en"])

    escalation = snapshot.get("escalation", {})
    if escalation.get("bullets"):
        lines.append(escalation["title"] + ": " + "; ".join(escalation["bullets"]))

    text = ". ".join(lines)
    return text[:3000]


def _build_content_hash(care_plan: CarePlan, language: str) -> str:
    raw = json.dumps(care_plan.plan_snapshot, sort_keys=True) + language
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post("/{care_plan_id}/tts", response_model=TtsResponse)
async def generate_care_plan_tts(care_plan_id: str, body: Optional[TtsRequest] = None, db: AsyncSession = Depends(get_db)):
    actual_body = body or TtsRequest()

    care_plan = (await db.execute(select(CarePlan).where(CarePlan.id == care_plan_id))).scalar()
    if not care_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Care plan not found")

    content_hash = _build_content_hash(care_plan, actual_body.language)

    existing_stmt = select(TemporaryAudio).where(
        TemporaryAudio.care_plan_id == care_plan_id,
        TemporaryAudio.content_hash == content_hash,
        TemporaryAudio.language == actual_body.language,
    ).order_by(TemporaryAudio.created_at.desc())
    existing = (await db.execute(existing_stmt)).scalar()

    now = ist_now()

    if existing:
        if existing.expires_at > now:
            return TtsResponse(asset_id=existing.id)
        if os.path.isfile(existing.file_path):
            os.remove(existing.file_path)
        if existing.generation_attempts >= MAX_TTS_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Max TTS generation attempts ({MAX_TTS_ATTEMPTS}) reached for this care plan.",
            )

    tts_text = _care_plan_to_tts_text(care_plan.plan_snapshot)
    if not tts_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Care plan has no speakable content")

    tts_text = await _translate_text(tts_text, actual_body.language)

    if not settings.SARVAM_API_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Sarvam API key not configured")

    headers = {"API-Subscription-Key": settings.SARVAM_API_KEY}
    sarvam_payload = {
        "text": tts_text, "target_language_code": actual_body.language,
        "speaker": "shubh", "model": "bulbul:v3", "pace": 1.0,
    }
    attempt = (existing.generation_attempts + 1) if existing else 1

    async with httpx.AsyncClient(timeout=60) as client:
        sarvam_resp = await client.post(f"{settings.SARVAM_BASE_URL}/text-to-speech", json=sarvam_payload, headers=headers)

    if sarvam_resp.status_code != 200:
        raise HTTPException(status_code=sarvam_resp.status_code, detail=f"Sarvam TTS failed: {sarvam_resp.text[:200]}")

    data = sarvam_resp.json()
    combined_b64 = "".join(data.get("audios", []))
    if not combined_b64:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Empty audio response from Sarvam")

    audio_bytes = base64.b64decode(combined_b64)
    TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    asset_id = str(uuid.uuid4())
    file_path = str(TEMP_AUDIO_DIR / f"{asset_id}.wav")
    with open(file_path, "wb") as f:
        f.write(audio_bytes)

    temp_audio = TemporaryAudio(
        id=asset_id, user_id=care_plan.user_id, care_plan_id=care_plan_id,
        content_hash=content_hash, language=actual_body.language, provider="sarvam", voice_id="shubh",
        file_path=file_path, mime_type="audio/wav", generation_attempts=attempt,
        expires_at=now + timedelta(hours=TTS_CACHE_TTL_HOURS),
    )
    db.add(temp_audio)
    await db.commit()
    await db.refresh(temp_audio)

    return TtsResponse(asset_id=asset_id)


@temp_audio_router.get("/{asset_id}")
async def stream_temporary_audio(asset_id: str, db: AsyncSession = Depends(get_db)):
    asset = (await db.execute(select(TemporaryAudio).where(TemporaryAudio.id == asset_id))).scalar()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio asset not found")
    if asset.expires_at < ist_now():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Audio asset has expired")
    if not os.path.isfile(asset.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found on disk")

    with open(asset.file_path, "rb") as f:
        audio_data = f.read()
    return StreamingResponse(io.BytesIO(audio_data), media_type=asset.mime_type or "audio/wav")
