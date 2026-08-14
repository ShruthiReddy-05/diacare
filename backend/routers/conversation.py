import json
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database import get_db
from models.user import User
from models.conversation import ConversationSession, ConversationResponse
from models.baseline_profile import BaselineProfile
from models.module_outcome import ModuleOutcome
from models.safety_event import SafetyEvent
from schemas.conversation import (
    ConversationSessionCreate, ConversationSessionResponse,
    ConversationResponseCreate, ConversationResponseOut, CompleteSittingRequest,
)
from services import b1_engine, b2_engine, b3_engine, m1_engine, m2_engine, m3_engine, m4_engine
from services import safety_engine
from services.checkin_scheduler import create_checkin_schedule
from utils import ist_now

router = APIRouter(prefix="/api/conversation", tags=["Conversation"])

_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "data" / "questionnaires" / "diafit_voice_baseline.json"
_script_cache: Dict[str, Any] = {}


def load_script() -> Dict[str, Any]:
    if not _script_cache:
        with open(_SCRIPT_PATH, "r", encoding="utf-8") as f:
            _script_cache.update(json.load(f))
    return _script_cache


@router.get("/script")
async def get_script():
    """The single source of truth for the conversation questionnaire -- the
    frontend fetches this rather than bundling a duplicate copy."""
    return load_script()


def get_save_as(question_id: str) -> str:
    script = load_script()
    for module in script.get("modules", []):
        for q in module.get("questions", []):
            if q["id"] == question_id:
                return q.get("save_as", question_id)
    return question_id


def _cast(val: str) -> Any:
    if not isinstance(val, str):
        return val
    low = val.strip().lower()
    if low in ("yes", "true"):
        return True
    if low in ("no", "false"):
        return False
    try:
        return float(val) if "." in val else int(val)
    except ValueError:
        return val


def _apply_save_as(answers: Dict[str, Any], question_id: str, raw_value: str) -> None:
    save_as = get_save_as(question_id)
    keys = save_as.split(",")
    if len(keys) == 1:
        answers[keys[0]] = _cast(raw_value)
        return
    # multi-part answers, e.g. "170,70" for heightCm,weightKg or "130,80" for bp
    parts = [p.strip() for p in str(raw_value).replace("/", ",").split(",")]
    for key, part in zip(keys, parts):
        answers[key] = _cast(part)


async def build_user_answers(user_id: str, db: AsyncSession) -> tuple[Dict[str, Any], set, str]:
    stmt = (
        select(ConversationResponse)
        .join(ConversationSession, ConversationSession.id == ConversationResponse.session_id)
        .where(ConversationSession.user_id == user_id)
        .order_by(ConversationResponse.answered_at.asc())
    )
    result = await db.execute(stmt)
    responses = result.scalars().all()

    answers: Dict[str, Any] = {}
    modules_seen = set()
    free_text_parts = []
    for resp in responses:
        _apply_save_as(answers, resp.question_id, resp.answer_value)
        modules_seen.add(resp.module_id)
        free_text_parts.append(resp.answer_value)
    return answers, modules_seen, " ".join(free_text_parts)


@router.post("/sessions", response_model=ConversationSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(user_id: str, session_in: ConversationSessionCreate, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    active_stmt = select(ConversationSession).where(
        ConversationSession.user_id == user_id,
        ConversationSession.status == "in_progress",
        ConversationSession.sitting == session_in.sitting,
    ).order_by(ConversationSession.started_at.desc())
    active = (await db.execute(active_stmt)).scalars().first()
    if active:
        stmt = select(ConversationSession).options(selectinload(ConversationSession.responses)).where(ConversationSession.id == active.id)
        return (await db.execute(stmt)).scalar()

    db_session = ConversationSession(
        user_id=user_id,
        script_id=session_in.script_id,
        script_version=session_in.script_version,
        sitting=session_in.sitting,
        preferred_checkin_time=session_in.preferred_checkin_time,
        status="in_progress",
    )
    db.add(db_session)
    await db.commit()

    stmt = select(ConversationSession).options(selectinload(ConversationSession.responses)).where(ConversationSession.id == db_session.id)
    return (await db.execute(stmt)).scalar()


@router.post("/sessions/{session_id}/responses", response_model=ConversationResponseOut)
async def add_response(session_id: str, response_in: ConversationResponseCreate, db: AsyncSession = Depends(get_db)):
    session = (await db.execute(select(ConversationSession).where(ConversationSession.id == session_id))).scalar()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found.")

    existing = (await db.execute(
        select(ConversationResponse).where(
            ConversationResponse.session_id == session_id,
            ConversationResponse.question_id == response_in.question_id,
        )
    )).scalar()

    if existing:
        existing.answer_value = response_in.answer_value
        existing.answer_display_label = response_in.answer_display_label
        existing.language = response_in.language
        existing.input_modality = response_in.input_modality
        existing.answered_at = ist_now()
        db_resp = existing
    else:
        db_resp = ConversationResponse(
            session_id=session_id,
            module_id=response_in.module_id,
            question_id=response_in.question_id,
            question_text_en=response_in.question_text_en,
            question_text_ta=response_in.question_text_ta,
            answer_value=response_in.answer_value,
            answer_display_label=response_in.answer_display_label,
            language=response_in.language,
            input_modality=response_in.input_modality,
        )
        db.add(db_resp)

    session.resume_module_id = response_in.module_id
    session.resume_question_id = response_in.question_id

    await db.commit()
    await db.refresh(db_resp)
    return db_resp


async def _upsert_baseline_profile(user_id: str, session_id: str, answers: Dict[str, Any], db: AsyncSession) -> BaselineProfile:
    b1 = b1_engine.compute_b1(answers)
    b2 = b2_engine.compute_b2(answers)
    b3 = b3_engine.compute_b3(answers, glycemic_category=b2["glycemic_category"])

    existing = (await db.execute(select(BaselineProfile).where(BaselineProfile.user_id == user_id))).scalar()
    values = {**b1, **b2, **b3, "session_id": session_id, "computed_at": ist_now()}
    if existing:
        for key, val in values.items():
            setattr(existing, key, val)
        profile = existing
    else:
        profile = BaselineProfile(user_id=user_id, **values)
        db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def _upsert_module_outcome(user_id: str, session_id: str, module_id: str, output: Dict[str, Any], db: AsyncSession) -> ModuleOutcome:
    existing = (await db.execute(
        select(ModuleOutcome).where(ModuleOutcome.user_id == user_id, ModuleOutcome.module_id == module_id)
    )).scalar()
    if existing:
        existing.output_json = output
        existing.session_id = session_id
        existing.computed_at = ist_now()
        outcome = existing
    else:
        outcome = ModuleOutcome(user_id=user_id, session_id=session_id, module_id=module_id, output_json=output)
        db.add(outcome)
    await db.commit()
    await db.refresh(outcome)
    return outcome


def _baseline_to_dict(profile: BaselineProfile) -> Dict[str, Any]:
    return {
        "age_band": profile.age_band, "bmi": profile.bmi, "bmi_category": profile.bmi_category,
        "waist_risk": profile.waist_risk, "sedentary_work_flag": profile.sedentary_work_flag,
        "glycemic_category": profile.glycemic_category, "duration_risk_flag": profile.duration_risk_flag,
        "bp_category": profile.bp_category, "regimen_class": profile.regimen_class,
        "hypoglycemia_risk_flag": profile.hypoglycemia_risk_flag, "herbal_use_flag": profile.herbal_use_flag,
        "follow_up_gap_flag": profile.follow_up_gap_flag, "screening_overdue": profile.screening_overdue,
        "complication_profile": profile.complication_profile, "foot_risk_category": profile.foot_risk_category,
        "exercise_clearance_required": profile.exercise_clearance_required,
        "tobacco_flag": profile.tobacco_flag, "alcohol_flag": profile.alcohol_flag,
        "overall_risk_tier": profile.overall_risk_tier,
    }


@router.post("/sessions/{session_id}/complete-sitting", response_model=ConversationSessionResponse)
async def complete_sitting(session_id: str, body: CompleteSittingRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(ConversationSession).options(selectinload(ConversationSession.responses)).where(ConversationSession.id == session_id)
    session = (await db.execute(stmt)).scalar()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found.")

    answers, modules_seen, free_text = await build_user_answers(session.user_id, db)

    # Module D safety check runs across every sitting -- structured red-flag
    # fields plus a keyword scan over every free-text answer given so far
    # (e.g. medications, missed-dose reason), so it also catches things like
    # an expression of self-harm that no structured question captures.
    triggered = safety_engine.check_safety(answers, free_text=free_text)
    for code in triggered:
        exists = (await db.execute(
            select(SafetyEvent).where(
                SafetyEvent.user_id == session.user_id, SafetyEvent.trigger_code == code, SafetyEvent.resolved == False,
            )
        )).scalar()
        if not exists:
            db.add(SafetyEvent(user_id=session.user_id, session_id=session_id, source_module=body.sitting, trigger_code=code))
    if triggered:
        await db.commit()

    baseline = None
    if {"B1", "B2", "B3"} & modules_seen or body.sitting == "1":
        baseline = await _upsert_baseline_profile(session.user_id, session_id, answers, db)

    if not baseline:
        baseline = (await db.execute(select(BaselineProfile).where(BaselineProfile.user_id == session.user_id))).scalar()

    if baseline and "M1" in modules_seen:
        nephropathy = (baseline.complication_profile or {}).get("nephropathy", False)
        m1_out = m1_engine.compute_m1(answers, bp_category=baseline.bp_category or "target",
                                       hypoglycemia_risk_flag=baseline.hypoglycemia_risk_flag, nephropathy=nephropathy)
        await _upsert_module_outcome(session.user_id, session_id, "M1", m1_out, db)

    if baseline and "M2" in modules_seen:
        m2_out = m2_engine.compute_m2(answers, sedentary_work_flag=baseline.sedentary_work_flag,
                                       hypoglycemia_risk_flag=baseline.hypoglycemia_risk_flag,
                                       exercise_clearance_required=baseline.exercise_clearance_required,
                                       foot_risk_category=baseline.foot_risk_category or "low")
        await _upsert_module_outcome(session.user_id, session_id, "M2", m2_out, db)

    if baseline and "M3" in modules_seen:
        m3_out = m3_engine.compute_m3(answers, regimen_class=baseline.regimen_class or "metformin_only",
                                       hypoglycemia_risk_flag=baseline.hypoglycemia_risk_flag,
                                       glycemic_category=baseline.glycemic_category or "unknown",
                                       age_band=baseline.age_band or "under_60")
        await _upsert_module_outcome(session.user_id, session_id, "M3", m3_out, db)

    if "M4" in modules_seen:
        m4_out = m4_engine.compute_m4(answers)
        await _upsert_module_outcome(session.user_id, session_id, "M4", m4_out, db)

        # Any expression of self-harm halts coaching immediately, per Module D --
        # m4_engine only classifies the answer, the safety module owns the escalation.
        if m4_out.get("self_harm_expressed") and "self_harm" not in triggered:
            exists = (await db.execute(
                select(SafetyEvent).where(
                    SafetyEvent.user_id == session.user_id, SafetyEvent.trigger_code == "self_harm", SafetyEvent.resolved == False,
                )
            )).scalar()
            if not exists:
                db.add(SafetyEvent(user_id=session.user_id, session_id=session_id, source_module=body.sitting, trigger_code="self_harm"))
                await db.commit()
            triggered.append("self_harm")

    session.status = "completed"
    session.completed_at = ist_now()
    await db.commit()

    if body.sitting == "3":
        try:
            await create_checkin_schedule(session.user_id, session.preferred_checkin_time or "evening", db)
        except Exception:
            pass

    stmt = select(ConversationSession).options(selectinload(ConversationSession.responses)).where(ConversationSession.id == session_id)
    return (await db.execute(stmt)).scalar()


@router.get("/sessions/{session_id}", response_model=ConversationSessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ConversationSession).options(selectinload(ConversationSession.responses)).where(ConversationSession.id == session_id)
    session = (await db.execute(stmt)).scalar()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found.")
    return session


@router.get("/user/{user_id}", response_model=List[ConversationSessionResponse])
async def get_user_sessions(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ConversationSession).options(selectinload(ConversationSession.responses)).where(
        ConversationSession.user_id == user_id
    ).order_by(ConversationSession.started_at.desc())
    return (await db.execute(stmt)).scalars().all()
