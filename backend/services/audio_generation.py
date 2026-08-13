"""
Shared audio generation logic used by both the CLI script and admin endpoint.
"""

import base64
import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models.audio_asset import AudioAsset
from database import Base

MEDIA_ROOT = Path(__file__).resolve().parent.parent / "media" / "audio" / "question-prompts"
QUESTIONNAIRES_DIR = Path(__file__).resolve().parent.parent / "data" / "questionnaires"
SARVAM_TTS_URL = f"{settings.SARVAM_BASE_URL}/text-to-speech"
LANGUAGES = {"en": "en-IN", "ta": "ta-IN"}


def resolve_prompt(question: dict, lang: str) -> str:
    tts_prompts = question.get("ttsPrompt", {})
    if isinstance(tts_prompts, dict) and lang in tts_prompts:
        return tts_prompts[lang]
    prompts = question.get("prompt", {})
    if isinstance(prompts, dict) and lang in prompts:
        return prompts[lang]
    return ""


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_questionnaires() -> list[dict]:
    if not QUESTIONNAIRES_DIR.exists():
        return []
    files = sorted(QUESTIONNAIRES_DIR.glob("*.json"))
    result = []
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            result.append(json.load(f))
    return result


async def call_sarvam_tts(text: str, language: str) -> Optional[bytes]:
    if not settings.SARVAM_API_KEY:
        return None
    headers = {"API-Subscription-Key": settings.SARVAM_API_KEY}
    payload = {
        "text": text,
        "target_language_code": language,
        "speaker": "shubh",
        "model": "bulbul:v3",
        "pace": 1.0,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(SARVAM_TTS_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                print(f"    Sarvam error {resp.status_code}: {resp.text[:300]}")
                return None
            data = resp.json()
            combined_b64 = "".join(data.get("audios", []))
            if not combined_b64:
                return None
            return base64.b64decode(combined_b64)
        except Exception as e:
            print(f"    Sarvam exception: {e}")
            return None


async def generate_for_questionnaire(
    db_session: AsyncSession,
    questionnaire: dict,
    lang_filter: Optional[str] = None,
    force_regen: bool = False,
) -> dict:
    """Generate audio for a single questionnaire. Returns a summary dict."""
    q_id = questionnaire["id"]
    q_version = questionnaire.get("version", "1.0.0")
    modules = questionnaire.get("modules", [])
    summary = {"generated": 0, "skipped": 0, "failed": 0, "errors": []}

    for mod in modules:
        for question in mod.get("questions", []):
            qq_id = question["id"]
            for lang_key, sarvam_lang in LANGUAGES.items():
                if lang_filter and lang_key != lang_filter:
                    continue

                text = resolve_prompt(question, lang_key)
                if not text:
                    summary["skipped"] += 1
                    continue

                ch = content_hash(text)

                if not force_regen:
                    stmt = select(AudioAsset).where(
                        AudioAsset.questionnaire_id == q_id,
                        AudioAsset.question_id == qq_id,
                        AudioAsset.language == lang_key,
                        AudioAsset.content_hash == ch,
                    )
                    result = await db_session.execute(stmt)
                    if result.scalar():
                        summary["skipped"] += 1
                        continue

                audio_data = await call_sarvam_tts(text, sarvam_lang)
                if audio_data is None:
                    summary["failed"] += 1
                    summary["errors"].append(f"{q_id}/{qq_id} ({lang_key}): TTS failed")
                    continue

                subdir = MEDIA_ROOT / q_id / q_version / lang_key
                subdir.mkdir(parents=True, exist_ok=True)
                filename = f"{qq_id}-{ch[:16]}.wav"
                file_path = subdir / filename
                with open(file_path, "wb") as f:
                    f.write(audio_data)

                relative_path = str(Path("media/audio/question-prompts") / q_id / q_version / lang_key / filename)
                new_asset = AudioAsset(
                    id=str(uuid.uuid4()),
                    questionnaire_id=q_id,
                    questionnaire_version=q_version,
                    question_id=qq_id,
                    language=lang_key,
                    provider="sarvam",
                    voice_id="shubh",
                    content_hash=ch,
                    file_path=relative_path,
                    mime_type="audio/wav",
                    duration_ms=None,
                )
                db_session.add(new_asset)
                await db_session.commit()
                summary["generated"] += 1

    return summary


async def run_generation(
    db_session: AsyncSession,
    questionnaire_id: Optional[str] = None,
    language: Optional[str] = None,
    force_regen: bool = False,
) -> dict:
    """Run audio generation for all or a specific questionnaire."""
    all_qs = load_questionnaires()
    if not all_qs:
        return {"error": "No questionnaire data files found"}

    if questionnaire_id:
        all_qs = [q for q in all_qs if q["id"] == questionnaire_id]
        if not all_qs:
            return {"error": f"Questionnaire '{questionnaire_id}' not found"}

    total = {"generated": 0, "skipped": 0, "failed": 0, "errors": []}
    for q in all_qs:
        s = await generate_for_questionnaire(db_session, q, language, force_regen)
        for k in ("generated", "skipped", "failed"):
            total[k] += s[k]
        total["errors"].extend(s["errors"])

    return total
