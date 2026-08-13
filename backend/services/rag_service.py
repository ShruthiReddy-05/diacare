from typing import List, Dict, Any
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.rag_rule import ExerciseRagRule

def build_health_tags(risk_result: Dict[str, Any], answers: Dict[str, Any], plan_type: str) -> List[str]:
    tags = []
    
    # BMI Category
    bmi_cat = risk_result.get("bmi_category")
    if bmi_cat == "overweight":
        tags.append("overweight")
    elif bmi_cat == "obese":
        tags.append("obese")
        tags.append("overweight") # obese implies overweight
        
    # Diabetes profile
    duration = answers.get("durationYears")
    if duration is not None:
        try:
            if float(duration) > 5:
                tags.append("duration_gt_5")
        except (ValueError, TypeError):
            pass
            
    if str(answers.get("medications")).lower() in ["insulin", "both"]:
        tags.append("uses_insulin")
        
    # Complications
    comp = risk_result.get("complication_flags", {})
    if comp.get("hasNeuropathySymptoms"):
        tags.append("neuropathy")
    if comp.get("hasEyeDisease"):
        tags.append("eye_disease")
    if comp.get("hasKidneyDisease"):
        tags.append("kidney_disease")
    if comp.get("hasFootWoundOrUlcer"):
        tags.append("foot_wounds")
    if comp.get("hasExerciseHypoglycemiaHistory"):
        tags.append("hypoglycemia_history")
    if comp.get("hasFallHistory"):
        tags.append("has_fall_history")
        
    # Sedentary
    if risk_result.get("sedentary") == "moderate_to_high":
        tags.append("sedentary_gt_4")
        
    # PAR-Q
    if risk_result.get("par_q_clearance_required") is True:
        tags.append("par_q_clearance")
        
    # Confidence & Motivation
    confidence = answers.get("confidenceLevel")
    if confidence is not None:
        try:
            if int(confidence) < 5:
                tags.append("low_confidence")
        except (ValueError, TypeError):
            pass
            
    # Barriers
    barriers = answers.get("exerciseBarriers", [])
    if isinstance(barriers, str):
        barriers = [b.strip() for b in barriers.split(",") if b.strip()]
        
    barriers_lower = [str(b).lower() for b in barriers]
    if any(any(x in b for x in ["time", "busy"]) for b in barriers_lower):
        tags.append("barrier_time")
    if any(any(x in b for x in ["pain", "fatigue", "tired", "joint"]) for b in barriers_lower):
        tags.append("barrier_pain_fatigue")
        
    # Sleep and stress
    sleep = answers.get("sleepHours")
    if sleep is not None:
        try:
            if float(sleep) < 6:
                tags.append("poor_sleep_stress")
        except (ValueError, TypeError):
            pass
            
    stress = str(answers.get("stressLevel", "")).lower()
    if stress in ["high", "moderate"]:
        if "poor_sleep_stress" not in tags:
            tags.append("poor_sleep_stress")
            
    # Junk food
    junk = str(answers.get("junkFoodFrequency", "")).lower()
    if junk in ["frequent", "daily", "often", "yes"]:
        tags.append("junk_food")
        
    # Plan template tags
    if plan_type == "plan_a_start_slowly":
        tags.append("plan_a")
    elif plan_type == "plan_b_fitt":
        tags.append("plan_b")
    elif plan_type == "medical_clearance_required":
        tags.append("par_q_clearance")
        
    # Strength is added unless severely contraindicated (like kidney disease or extreme high blood sugar, 
    # but we seed the strength rule and let prescription validator filter it later)
    tags.append("strength")
    
    return list(set(tags))

async def retrieve_applicable_rules(session: AsyncSession, health_tags: List[str]) -> List[ExerciseRagRule]:
    # Query all approved rules
    stmt = select(ExerciseRagRule).where(ExerciseRagRule.review_status == "approved")
    result = await session.execute(stmt)
    all_rules = result.scalars().all()
    
    applicable = []
    for rule in all_rules:
        # A rule matches if any of its condition tags are in the user's health tags
        if any(tag in health_tags for tag in rule.condition_tags):
            applicable.append(rule)
            
    # Sort by precedence (lower number = higher priority/safety precedence)
    applicable.sort(key=lambda r: r.precedence)
    return applicable
