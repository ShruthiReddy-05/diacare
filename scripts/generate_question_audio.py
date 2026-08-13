"""
Script to pre-generate question prompt audio using Sarvam AI TTS.

Usage:
    python -m scripts.generate_question_audio                          # generate all
    python -m scripts.generate_question_audio --questionnaire-id initial_assessment
    python -m scripts.generate_question_audio --language ta
    python -m scripts.generate_question_audio --regen                   # force re-generate

Run from backend/ directory so that imports resolve correctly.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import settings
from services.audio_generation import (
    load_questionnaires,
    run_generation,
    MEDIA_ROOT,
)
from database import Base


async def main():
    parser = argparse.ArgumentParser(description="Pre-generate question audio via Sarvam TTS")
    parser.add_argument("--db-url", default=settings.DATABASE_URL, help="Database URL")
    parser.add_argument("--questionnaire-id", default=None, help="Only process this questionnaire ID")
    parser.add_argument("--language", default=None, choices=["en", "ta"], help="Only generate for this language")
    parser.add_argument("--regen", action="store_true", help="Force re-generate even if hash matches")
    args = parser.parse_args()

    all_qs = load_questionnaires()
    if not all_qs:
        print("No questionnaire data files found.")
        return

    if args.questionnaire_id:
        all_qs = [q for q in all_qs if q["id"] == args.questionnaire_id]
        if not all_qs:
            print(f"Questionnaire '{args.questionnaire_id}' not found.")
            return

    connect_args = {}
    if args.db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    engine = create_async_engine(args.db_url, echo=False, connect_args=connect_args)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    print(f"Media root: {MEDIA_ROOT}")
    print(f"Generating audio for {len(all_qs)} questionnaire(s)...\n")

    async with async_session() as session:
        summary = await run_generation(session, args.questionnaire_id, args.language, args.regen)

    print(f"\nDone. Generated: {summary.get('generated', 0)}, "
          f"Skipped: {summary.get('skipped', 0)}, "
          f"Failed: {summary.get('failed', 0)}")
    if summary.get("errors"):
        for e in summary["errors"]:
            print(f"  Error: {e}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
