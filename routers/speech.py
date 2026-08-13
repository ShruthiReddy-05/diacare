import base64
import httpx
import io
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from config import settings

router = APIRouter(prefix="/api/speech", tags=["Speech Proxy"])

SARVAM_TTS_URL = f"{settings.SARVAM_BASE_URL}/text-to-speech"
SARVAM_ASR_URL = f"{settings.SARVAM_BASE_URL}/speech-to-text"
SARVAM_TRANSLATE_URL = f"{settings.SARVAM_BASE_URL}/translate"


class TtsRequest(BaseModel):
    text: str
    target_language_code: str = "ta-IN"
    speaker: str = "shubh"
    model: str = "bulbul:v3"
    pace: float = 1.0


class AsrRequest(BaseModel):
    audio_base64: str
    language: str = "ta-IN"
    model: str = "saaras:v3"


@router.post("/tts")
async def proxy_tts(body: TtsRequest):
    if not settings.SARVAM_API_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Sarvam API key not configured")
    headers = {"API-Subscription-Key": settings.SARVAM_API_KEY}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(SARVAM_TTS_URL, json=body.model_dump(), headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=f"Sarvam TTS failed: {resp.text[:200]}")
    data = resp.json()
    combined_b64 = "".join(data.get("audios", []))
    if not combined_b64:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Empty audio response from Sarvam")
    audio_data = base64.b64decode(combined_b64)
    return StreamingResponse(io.BytesIO(audio_data), media_type="audio/wav")


@router.post("/asr")
async def proxy_asr(body: AsrRequest):
    if not settings.SARVAM_API_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Sarvam API key not configured")
    audio_bytes = base64.b64decode(body.audio_base64)
    headers = {"API-Subscription-Key": settings.SARVAM_API_KEY}

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Transcribe Tamil speech → Tamil text
        files = {"file": ("audio.webm", audio_bytes, "audio/webm")}
        asr_data = {"language_code": body.language, "model": body.model, "mode": "transcribe"}
        asr_resp = await client.post(SARVAM_ASR_URL, headers=headers, files=files, data=asr_data)

    if asr_resp.status_code != 200:
        detail = asr_resp.text[:200]
        try:
            detail = asr_resp.json().get("error", {}).get("message", detail)
        except Exception:
            pass
        raise HTTPException(status_code=asr_resp.status_code, detail=f"Sarvam ASR failed: {detail}")

    result = asr_resp.json()
    tamil_text = result.get("transcript", "")

    if not tamil_text:
        return {"transcript": "", "display_text": ""}

    # Step 2: Translate Tamil text → English
    translate_payload = {
        "input": tamil_text,
        "source_language_code": "ta-IN",
        "target_language_code": "en-IN",
        "model": "mayura:v1",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        tr_resp = await client.post(SARVAM_TRANSLATE_URL, json=translate_payload, headers=headers)

    english_text = tamil_text
    if tr_resp.status_code == 200:
        tr_data = tr_resp.json()
        english_text = tr_data.get("translated_text", tamil_text)

    return {"transcript": english_text, "display_text": tamil_text}
