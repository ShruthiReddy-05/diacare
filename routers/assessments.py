from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

from database import get_db
from models.user import User
from models.assessment import AssessmentSession, QuestionResponse, RiskResult
from schemas.assessment import (
    AssessmentSessionCreate, AssessmentSessionResponse,
    QuestionResponseCreate, QuestionResponseResponse
)
from services.follow_up_scheduler import create_default_schedule
from services.risk_engine import (
    calculate_bmi, classify_bmi, classify_glycemic,
    calculate_met_min_week, classify_physical_activity, classify_sedentary,
    evaluate_par_q, build_complication_flags, calculate_overall_risk
)
from utils import ist_now

# Maps questionnaire question_id -> saveAs key for the answers dict
QUESTION_ID_TO_SAVE_AS = {
    "shall_we_begin": "shallBegin",
    "age": "age",
    "gender": "gender",
    "height_weight": "height_weight",  # special: extract heightCm/weightKg
    "duration": "durationYears",
    "knows_hba1c": "knowsHbA1c",
    "hba1c": "hba1c",
    "knows_fasting": "knowsFasting",
    "fasting_sugar": "fastingSugar",
    "medications": "medications",
    "hypertension": "hasHypertension",
    "neuropathy": "hasNeuropathySymptoms",
    "eye_disease": "hasEyeDisease",
    "kidney_disease": "hasKidneyDisease",
    "foot_wound": "hasFootWoundOrUlcer",
    "hypo_history": "hasExerciseHypoglycemiaHistory",
    "fall_history": "hasFallHistory",
    "vigorous_days": "vigorousDays",
    "vigorous_minutes": "vigorousMinutes",
    "moderate_days": "moderateDays",
    "moderate_minutes": "moderateMinutes",
    "walking_days": "walkingDays",
    "walking_minutes": "walkingMinutes",
    "sitting_hours": "sittingHours",
    "parq_heart": "parqHeartCondition",
    "parq_chest_active": "parqChestPainActivity",
    "parq_chest_rest": "parqChestPainRest",
    "parq_balance": "parqDizziness",
    "parq_bone": "parqBoneJoint",
    "parq_drugs": "parqDrugs",
    "parq_other": "parqOtherReason",
    "confidence": "confidenceLevel",
    "exercise_types": "preferredExerciseTypes",
    "enjoyment": "enjoymentScore",
    "barriers": "exerciseBarriers",
    "sleep_hours": "sleepHours",
    "stress": "stressLevel",
    "junk_food": "junkFoodFrequency",
    "view_prescription": "wantsPrescription",
}

router = APIRouter(prefix="/api/assessments", tags=["Assessments"])

@router.post("/sessions", response_model=AssessmentSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(user_id: str, session_in: AssessmentSessionCreate, db: AsyncSession = Depends(get_db)):
    # Verify user exists
    user_stmt = select(User).where(User.id == user_id)
    user_res = await db.execute(user_stmt)
    if not user_res.scalar():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
        
    # Check if there's already an active (in_progress) session for this user
    active_stmt = select(AssessmentSession).where(
        AssessmentSession.user_id == user_id,
        AssessmentSession.status == "in_progress"
    )
    active_res = await db.execute(active_stmt)
    active_session = active_res.scalar()
    
    if active_session:
        # Reset started_at so avg completion time doesn't include idle gaps
        active_session.started_at = ist_now()
        await db.commit()
        # Return existing active session instead of creating a new one (resumable)
        stmt = select(AssessmentSession).options(
            selectinload(AssessmentSession.responses),
            selectinload(AssessmentSession.risk_results)
        ).where(AssessmentSession.id == active_session.id)
        res = await db.execute(stmt)
        return res.scalar()
        
    db_session = AssessmentSession(
        user_id=user_id,
        questionnaire_id=session_in.questionnaire_id,
        questionnaire_version=session_in.questionnaire_version,
        status="in_progress"
    )
    db.add(db_session)
    await db.commit()
    
    # Reload session with relationships
    stmt = select(AssessmentSession).options(
        selectinload(AssessmentSession.responses),
        selectinload(AssessmentSession.risk_results)
    ).where(AssessmentSession.id == db_session.id)
    res = await db.execute(stmt)
    return res.scalar()

@router.post("/sessions/{session_id}/responses", response_model=QuestionResponseResponse)
async def add_response(session_id: str, response_in: QuestionResponseCreate, db: AsyncSession = Depends(get_db)):
    # Verify session exists
    session_stmt = select(AssessmentSession).where(AssessmentSession.id == session_id)
    session_res = await db.execute(session_stmt)
    session = session_res.scalar()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment session not found."
        )
        
    # Check if this question was already answered in this session; if so, update it
    existing_stmt = select(QuestionResponse).where(
        QuestionResponse.session_id == session_id,
        QuestionResponse.question_id == response_in.question_id
    )
    existing_res = await db.execute(existing_stmt)
    db_resp = existing_res.scalar()
    
    if db_resp:
        db_resp.answer_value = response_in.answer_value
        db_resp.answer_display_label = response_in.answer_display_label
        db_resp.language = response_in.language
        db_resp.answered_at = ist_now()
    else:
        db_resp = QuestionResponse(
            session_id=session_id,
            question_id=response_in.question_id,
            module_id=response_in.module_id,
            question_text_en=response_in.question_text_en,
            question_text_ta=response_in.question_text_ta,
            answer_value=response_in.answer_value,
            answer_display_label=response_in.answer_display_label,
            language=response_in.language
        )
        db.add(db_resp)
        
    await db.commit()
    await db.refresh(db_resp)
    return db_resp

@router.post("/sessions/{session_id}/complete", response_model=AssessmentSessionResponse)
async def complete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    # Load session with responses
    stmt = select(AssessmentSession).options(
        selectinload(AssessmentSession.responses)
    ).where(AssessmentSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment session not found."
        )
        
    # Extract answers dictionary from responses, mapping question_id -> saveAs key
    answers = {}
    height_cm = None
    weight_kg = None

    for resp in session.responses:
        val = resp.answer_value
        # Attempt to cast boolean or numeric strings
        if isinstance(val, str):
            val_lower = val.lower()
            if val_lower == "yes":
                cast_val = True
            elif val_lower == "no":
                cast_val = False
            elif val_lower == "true":
                cast_val = True
            elif val_lower == "false":
                cast_val = False
            else:
                try:
                    if "." in val:
                        cast_val = float(val)
                    else:
                        cast_val = int(val)
                except ValueError:
                    cast_val = val
        else:
            cast_val = val

        # Map question_id to saveAs key
        save_as = QUESTION_ID_TO_SAVE_AS.get(resp.question_id, resp.question_id)

        # Special handling: height_weight stores "170cm,70kg" format
        if resp.question_id == "height_weight" and isinstance(val, str) and "cm" in val:
            parts = val.replace("cm", "").replace("kg", "").split(",")
            if len(parts) >= 2:
                try:
                    height_cm_val = float(parts[0].strip())
                    weight_kg_val = float(parts[1].strip())
                    height_cm = height_cm_val
                    weight_kg = weight_kg_val
                    answers["heightCm"] = height_cm_val
                    answers["weightKg"] = weight_kg_val
                    continue
                except ValueError:
                    pass

        answers[save_as] = cast_val

    # Parse key health parameters (use saveAs keys)
    height = answers.get("heightCm") or height_cm
    weight = answers.get("weightKg") or weight_kg
    hba1c = answers.get("hba1c")
    fasting_sugar = answers.get("fastingSugar")
    
    # Calculate MET-min/week from IPAQ responses
    met_min_week = calculate_met_min_week(answers)
    
    # Sitting hours
    from services.risk_engine import safe_float
    sitting_hours = safe_float(answers.get("sittingHours"))
    
    # Run risk engine
    bmi = calculate_bmi(height, weight)
    bmi_category = classify_bmi(bmi)
    glycemic = classify_glycemic(hba1c=hba1c, fasting_sugar=fasting_sugar)
    physical_activity = classify_physical_activity(met_min_week)
    sedentary = classify_sedentary(sitting_hours)
    
    # Par-Q answers use saveAs keys
    par_q_answers = {
        "parqHeartCondition": answers.get("parqHeartCondition", False),
        "parqChestPainActivity": answers.get("parqChestPainActivity", False),
        "parqChestPainRest": answers.get("parqChestPainRest", False),
        "parqDizziness": answers.get("parqDizziness", False),
        "parqBoneJoint": answers.get("parqBoneJoint", False),
        "parqDrugs": answers.get("parqDrugs", False),
        "parqOtherReason": answers.get("parqOtherReason", False),
    }
    par_q_clearance = evaluate_par_q(par_q_answers)
    
    complication_answers = {
        "hasHypertension": answers.get("hasHypertension", False),
        "hasNeuropathySymptoms": answers.get("hasNeuropathySymptoms", False),
        "hasEyeDisease": answers.get("hasEyeDisease", False),
        "hasKidneyDisease": answers.get("hasKidneyDisease", False),
        "hasFootWoundOrUlcer": answers.get("hasFootWoundOrUlcer", False),
        "hasExerciseHypoglycemiaHistory": answers.get("hasExerciseHypoglycemiaHistory", False),
        "hasFallHistory": answers.get("hasFallHistory", False),
    }
    complication_flags = build_complication_flags(complication_answers)
    
    overall = calculate_overall_risk(
        glycemic, physical_activity, sedentary, par_q_clearance, complication_flags
    )
    
    # Delete any existing risk results for this session (idempotency)
    delete_risk_stmt = select(RiskResult).where(RiskResult.session_id == session_id)
    delete_res = await db.execute(delete_risk_stmt)
    for existing_risk in delete_res.scalars().all():
        await db.delete(existing_risk)
        
    # Create RiskResult entry
    db_risk = RiskResult(
        session_id=session_id,
        user_id=session.user_id,
        glycemic=glycemic,
        physical_activity=physical_activity,
        sedentary=sedentary,
        lifestyle="low", # default placeholder for Phase 1
        bmi_category=bmi_category,
        par_q_clearance_required=par_q_clearance,
        complication_flags=complication_flags,
        overall=overall
    )
    db.add(db_risk)
    
    # Complete the session
    session.status = "completed"
    session.completed_at = ist_now()
    
    await db.commit()
    
    # Auto-create follow-up schedule for the user
    try:
        await create_default_schedule(session.user_id, db)
    except Exception:
        pass
    
    # Return full session details including responses and risk results
    stmt = select(AssessmentSession).options(
        selectinload(AssessmentSession.responses),
        selectinload(AssessmentSession.risk_results)
    ).where(AssessmentSession.id == session_id)
    res = await db.execute(stmt)
    return res.scalar()

@router.get("/sessions/{session_id}", response_model=AssessmentSessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AssessmentSession).options(
        selectinload(AssessmentSession.responses),
        selectinload(AssessmentSession.risk_results)
    ).where(AssessmentSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment session not found."
        )
    return session

@router.get("/user/{user_id}", response_model=List[AssessmentSessionResponse])
async def get_user_sessions(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AssessmentSession).options(
        selectinload(AssessmentSession.responses),
        selectinload(AssessmentSession.risk_results)
    ).where(AssessmentSession.user_id == user_id).order_by(AssessmentSession.started_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
