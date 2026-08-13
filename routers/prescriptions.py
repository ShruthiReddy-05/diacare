import asyncio
import base64
import hashlib
import io
import httpx
import json
import logging
import os
import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from pydantic import BaseModel
from pathlib import Path

from database import get_db
from models.assessment import AssessmentSession, RiskResult
from models.prescription import Prescription, AiPrescriptionRequest, AiPrescriptionOutput
from models.temporary_audio import TemporaryAudio
from schemas.prescription import PrescriptionResponse
from services.prescription_generator import generate_prescription
from config import settings
from routers.assessments import QUESTION_ID_TO_SAVE_AS
from utils import ist_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prescriptions", tags=["Prescriptions"])
temp_audio_router = APIRouter(prefix="/api/temporary-audio", tags=["Temporary Audio"])

SARVAM_TRANSLATE_URL = f"{settings.SARVAM_BASE_URL}/translate"

async def translate_text(text: str, source: str = "en-IN", target: str = "ta-IN") -> str:
    if not text or not text.strip() or not settings.SARVAM_API_KEY:
        return text
    headers = {"API-Subscription-Key": settings.SARVAM_API_KEY}
    payload = {"input": text, "source_language_code": source, "target_language_code": target, "model": "mayura:v1"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(SARVAM_TRANSLATE_URL, json=payload, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("translated_text", text)
    except Exception:
        pass
    return text

TEXT_FIELDS = {"activityName", "duration", "frequency", "progressionRule", "safetyReason"}

async def translate_exercise(ex: dict) -> dict:
    ex = dict(ex)
    tasks = {f: translate_text(ex[f]) for f in TEXT_FIELDS if f in ex and ex[f]}
    if tasks:
        results = await asyncio.gather(*tasks.values())
        for f, val in zip(tasks.keys(), results):
            ex[f] = val
    return ex

async def translate_prescription_snapshot(snapshot: dict) -> dict:
    translated = dict(snapshot)
    if "userSummary" in translated:
        translated["userSummary"] = await translate_text(translated["userSummary"])
    for key in ("activityPlan", "simpleActivities", "strengthExercises"):
        if key in translated:
            translated[key] = await asyncio.gather(*[translate_exercise(e) for e in translated[key]])
    if "personalizedTips" in translated:
        async def translate_tip(tip: dict) -> dict:
            tip = dict(tip)
            if tip.get("tipText"):
                tip["tipText"] = await translate_text(tip["tipText"])
            if tip.get("rationale"):
                tip["rationale"] = await translate_text(tip["rationale"])
            return tip
        translated["personalizedTips"] = await asyncio.gather(*[translate_tip(t) for t in translated["personalizedTips"]])
    if "safetyWarnings" in translated:
        translated["safetyWarnings"] = await asyncio.gather(*[translate_text(w) for w in translated["safetyWarnings"]])
    return translated

@router.post("/generate", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def generate_user_prescription(session_id: str, language: str = Query("en"), db: AsyncSession = Depends(get_db)):
    # 1. Load session and responses
    session_stmt = select(AssessmentSession).options(
        selectinload(AssessmentSession.responses)
    ).where(AssessmentSession.id == session_id)
    session_res = await db.execute(session_stmt)
    session = session_res.scalar()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment session not found."
        )
        
    if session.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment session is not completed. Cannot generate prescription."
        )
        
    # 2. Load latest risk result
    risk_stmt = select(RiskResult).where(RiskResult.session_id == session_id).order_by(RiskResult.computed_at.desc())
    risk_res = await db.execute(risk_stmt)
    risk_record = risk_res.scalar()
    
    if not risk_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Risk results not found for this session. Please complete the assessment first."
        )
        
    # Prepare answers dict — use saveAs keys (same mapping as complete_session)
    answers = {}
    for resp in session.responses:
        val = resp.answer_value
        if not isinstance(val, str):
            cast_val = val
        elif val.lower() == "yes":
            cast_val = True
        elif val.lower() == "no":
            cast_val = False
        elif val.lower() == "true":
            cast_val = True
        elif val.lower() == "false":
            cast_val = False
        else:
            try:
                if "." in val:
                    cast_val = float(val)
                else:
                    cast_val = int(val)
            except ValueError:
                cast_val = val

        # Map question_id -> saveAs, same as complete_session
        if resp.question_id == "height_weight" and isinstance(val, str) and "cm" in val:
            parts = val.replace("cm", "").replace("kg", "").split(",")
            if len(parts) >= 2:
                try:
                    answers["heightCm"] = float(parts[0].strip())
                    answers["weightKg"] = float(parts[1].strip())
                    continue
                except ValueError:
                    pass

        save_as = QUESTION_ID_TO_SAVE_AS.get(resp.question_id, resp.question_id)
        answers[save_as] = cast_val
        
    risk_dict = {
        "glycemic": risk_record.glycemic,
        "physical_activity": risk_record.physical_activity,
        "sedentary": risk_record.sedentary,
        "bmi_category": risk_record.bmi_category,
        "par_q_clearance_required": risk_record.par_q_clearance_required,
        "complication_flags": risk_record.complication_flags,
        "overall": risk_record.overall
    }
    
    # 3. Call prescription generator
    gen_result = await generate_prescription(
        db, session.user_id, session.id, risk_dict, answers
    )
    
    plan_type = gen_result["plan_type"]
    prescription_snapshot = gen_result["prescription_snapshot"]
    validation_status = gen_result["validation_status"]
    
    # 3b. Translate prescription snapshot if language is Tamil
    if language == "ta":
        prescription_snapshot = await translate_prescription_snapshot(prescription_snapshot)
    rejection_reason = gen_result["rejection_reason"]
    rag_source_ids = gen_result["rag_source_ids"]
    
    # 4. Create AiPrescriptionRequest record
    ai_request = AiPrescriptionRequest(
        user_id=session.user_id,
        session_id=session.id,
        model_provider="together" if settings.TOGETHER_API_KEY else "rule_based_fallback",
        model_name=settings.get_llm_model() if settings.TOGETHER_API_KEY else "rule_based_fallback",
        temperature=settings.LLM_TEMPERATURE,
        normalized_health_profile_json=answers,
        retrieved_rag_rule_ids=rag_source_ids
    )
    db.add(ai_request)
    await db.flush() # Populate request ID
    
    # 5. Create final Prescription record
    db_prescription = Prescription(
        user_id=session.user_id,
        session_id=session.id,
        plan_type=plan_type,
        prescription_snapshot=prescription_snapshot
    )
    db.add(db_prescription)
    await db.flush() # Populate prescription ID
    
    # 6. Create AiPrescriptionOutput record
    ai_output = AiPrescriptionOutput(
        request_id=ai_request.id,
        raw_model_output_json=prescription_snapshot, # in fallback, raw matches validated
        validated_output_json=prescription_snapshot,
        validation_status=validation_status,
        rejection_reason=rejection_reason,
        final_prescription_id=db_prescription.id
    )
    db.add(ai_output)
    
    await db.commit()
    await db.refresh(db_prescription)
    return db_prescription

@router.get("/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription_by_id(prescription_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Prescription).where(Prescription.id == prescription_id)
    result = await db.execute(stmt)
    pres = result.scalar()
    if not pres:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found."
        )
    return pres

@router.get("/user/{user_id}/latest", response_model=PrescriptionResponse)
async def get_latest_user_prescription(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Prescription).where(Prescription.user_id == user_id).order_by(Prescription.created_at.desc())
    result = await db.execute(stmt)
    pres = result.scalar()
    if not pres:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No prescription found for this user."
        )
    return pres


# ── Prescription TTS Cache ──────────────────────────────────────────────────

MAX_TTS_ATTEMPTS = 3
TEMP_AUDIO_DIR = Path(__file__).resolve().parent.parent / "temp_audio_cache"
TTS_CACHE_TTL_HOURS = 48

class TtsResponse(BaseModel):
    asset_id: str

class TtsRequest(BaseModel):
    language: str = "en-IN"

def _prescription_to_tts_text(snapshot: dict, language: str) -> str:
    """Build a spoken summary from the prescription snapshot."""
    lines = []
    summary = snapshot.get("userSummary", "")
    if summary:
        lines.append(summary)

    for key in ("activityPlan", "simpleActivities", "strengthExercises"):
        exercises = snapshot.get(key, []) or []
        for ex in exercises:
            name = ex.get("activityName", "")
            duration = ex.get("duration", "")
            freq = ex.get("frequency", "")
            if name:
                parts = [name]
                if duration:
                    parts.append(f"for {duration}")
                if freq:
                    parts.append(freq)
                lines.append(". ".join(parts))

    tips = snapshot.get("personalizedTips", []) or []
    for tip in tips:
        txt = tip.get("tipText", "")
        if txt:
            lines.append(txt)

    warnings = snapshot.get("safetyWarnings", []) or []
    for w in warnings:
        if w:
            lines.append(w)

    text = ". ".join(lines)
    if len(text) > 3000:
        text = text[:3000]
    return text

async def _build_content_hash(prescription: Prescription, language: str) -> str:
    raw = json.dumps(prescription.prescription_snapshot, sort_keys=True) + language
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post("/{prescription_id}/tts", response_model=TtsResponse)
async def generate_prescription_tts(
    prescription_id: str,
    body: Optional[TtsRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    actual_body = body or TtsRequest()

    stmt = select(Prescription).where(Prescription.id == prescription_id)
    result = await db.execute(stmt)
    pres = result.scalar()
    if not pres:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")

    content_hash = await _build_content_hash(pres, actual_body.language)

    existing_stmt = select(TemporaryAudio).where(
        TemporaryAudio.prescription_id == prescription_id,
        TemporaryAudio.content_hash == content_hash,
        TemporaryAudio.language == actual_body.language,
    ).order_by(TemporaryAudio.created_at.desc())
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar()

    now = ist_now()

    if existing:
        if existing.expires_at > now:
            return TtsResponse(asset_id=existing.id)
        os.remove(existing.file_path)

    if existing and existing.generation_attempts >= MAX_TTS_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Max TTS generation attempts ({MAX_TTS_ATTEMPTS}) reached for this prescription."
        )

    tts_text = _prescription_to_tts_text(pres.prescription_snapshot, actual_body.language)
    if not tts_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prescription has no speakable content")

    if not settings.SARVAM_API_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Sarvam API key not configured")

    headers = {"API-Subscription-Key": settings.SARVAM_API_KEY}
    sarvam_payload = {
        "text": tts_text,
        "target_language_code": actual_body.language,
        "speaker": "shubh",
        "model": "bulbul:v3",
        "pace": 1.0,
    }

    attempt = (existing.generation_attempts + 1) if existing else 1

    async with httpx.AsyncClient(timeout=60) as client:
        sarvam_resp = await client.post(
            f"{settings.SARVAM_BASE_URL}/text-to-speech",
            json=sarvam_payload,
            headers=headers,
        )

    if sarvam_resp.status_code != 200:
        raise HTTPException(
            status_code=sarvam_resp.status_code,
            detail=f"Sarvam TTS failed: {sarvam_resp.text[:200]}"
        )

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
        id=asset_id,
        user_id=pres.user_id,
        prescription_id=prescription_id,
        content_hash=content_hash,
        language=actual_body.language,
        provider="sarvam",
        voice_id="shubh",
        file_path=file_path,
        mime_type="audio/wav",
        generation_attempts=attempt,
        expires_at=now + timedelta(hours=TTS_CACHE_TTL_HOURS),
    )
    db.add(temp_audio)
    await db.commit()
    await db.refresh(temp_audio)

    return TtsResponse(asset_id=asset_id)


@temp_audio_router.get("/{asset_id}")
async def stream_temporary_audio(asset_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(TemporaryAudio).where(TemporaryAudio.id == asset_id)
    result = await db.execute(stmt)
    asset = result.scalar()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio asset not found")
    if asset.expires_at < ist_now():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Audio asset has expired")
    if not os.path.isfile(asset.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found on disk")

    with open(asset.file_path, "rb") as f:
        audio_data = f.read()
    return StreamingResponse(io.BytesIO(audio_data), media_type=asset.mime_type or "audio/wav")
