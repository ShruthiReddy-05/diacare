from typing import Optional, Dict, Any


def safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def calculate_bmi(height_cm: Optional[float], weight_kg: Optional[float]) -> float:
    if not height_cm or not weight_kg or height_cm <= 0:
        return 0.0
    return round(weight_kg / ((height_cm / 100) ** 2), 2)

def classify_bmi(bmi: float) -> str:
    if bmi <= 0:
        return "unknown"
    if bmi < 18.5:
        return "underweight"
    if bmi <= 22.9:
        return "normal"
    if bmi <= 27.4:
        return "overweight"
    return "obese"

def classify_glycemic(hba1c: Any = None, fasting_sugar: Any = None) -> str:
    h = safe_float(hba1c)
    f = safe_float(fasting_sugar)
    if f and f > 300:
        return "red_flag"
    if h:
        if h < 7.0:
            return "good"
        elif h <= 9.0:
            return "moderate"
        else:
            return "high"
    if f:
        if f < 130:
            return "good"
        elif f <= 180:
            return "moderate"
        else:
            return "high"
    return "unknown"

def calculate_met_min_week(answers: Dict[str, Any]) -> float:
    vigorous_days = safe_float(answers.get("vigorousDays"))
    vigorous_minutes = safe_float(answers.get("vigorousMinutes"))
    moderate_days = safe_float(answers.get("moderateDays"))
    moderate_minutes = safe_float(answers.get("moderateMinutes"))
    walking_days = safe_float(answers.get("walkingDays"))
    walking_minutes = safe_float(answers.get("walkingMinutes"))

    vigorous_met = vigorous_days * vigorous_minutes * 8.0
    moderate_met = moderate_days * moderate_minutes * 4.0
    walking_met = walking_days * walking_minutes * 3.3

    return round(vigorous_met + moderate_met + walking_met, 2)

def classify_physical_activity(met_min_per_week: float) -> str:
    if met_min_per_week >= 3000:
        return "adequate"
    elif met_min_per_week >= 600:
        return "moderate"
    else:
        return "low"

def classify_sedentary(sitting_hours: float) -> str:
    if sitting_hours < 4.0:
        return "low"
    else:
        return "moderate_to_high"

def evaluate_par_q(answers: Dict[str, Any]) -> bool:
    parq_keys = [
        "parqHeartCondition",
        "parqChestPainActivity",
        "parqChestPainRest",
        "parqDizziness",
        "parqBoneJoint",
        "parqDrugs",
        "parqOtherReason"
    ]
    return any(answers.get(key) is True for key in parq_keys)

def build_complication_flags(answers: Dict[str, Any]) -> Dict[str, bool]:
    return {
        "hasHypertension": bool(answers.get("hasHypertension", False)),
        "hasNeuropathySymptoms": bool(answers.get("hasNeuropathySymptoms", False)),
        "hasEyeDisease": bool(answers.get("hasEyeDisease", False)),
        "hasKidneyDisease": bool(answers.get("hasKidneyDisease", False)),
        "hasFootWoundOrUlcer": bool(answers.get("hasFootWoundOrUlcer", False)),
        "hasExerciseHypoglycemiaHistory": bool(answers.get("hasExerciseHypoglycemiaHistory", False)),
        "hasFallHistory": bool(answers.get("hasFallHistory", False)),
    }

def classify_hypoglycemia_risk(answers: Dict[str, Any]) -> str:
    uses_insulin = bool(answers.get("usesInsulin", False))
    has_hypo_history = bool(answers.get("hasExerciseHypoglycemiaHistory", False))
    medications = str(answers.get("medications", "")).lower()
    
    # Check sulfonylureas
    sulfonylureas = ["glimepiride", "gliclazide", "glipizide", "sulfonylurea", "amaryl", "diamicron"]
    uses_sulfonylurea = any(med in medications for med in sulfonylureas)
    
    if uses_insulin or has_hypo_history:
        return "high"
    elif uses_sulfonylurea:
        return "moderate"
    return "low"

def select_plan_type(risk_result: Dict[str, Any], answers: Dict[str, Any]) -> str:
    par_q_required = bool(risk_result.get("par_q_clearance_required", False))
    complication_flags = risk_result.get("complication_flags", {})
    glycemic = risk_result.get("glycemic", "unknown")
    bmi_category = risk_result.get("bmi_category", "unknown")
    pa_status = risk_result.get("physical_activity", "low")
    
    # Check HbA1c ≥ 8% — clinical review required
    hba1c = safe_float(answers.get("hba1c"))
    hba1c_high = hba1c >= 8.0

    # 1. Check severe / clearance required conditions
    if par_q_required or complication_flags.get("hasKidneyDisease") or glycemic == "red_flag" or hba1c_high:
        return "medical_clearance_required"
        
    # 2. Check Plan A (Start Slowly) indicators
    has_complications = any(complication_flags.get(key) for key in [
        "hasNeuropathySymptoms",
        "hasEyeDisease",
        "hasFootWoundOrUlcer",
        "hasExerciseHypoglycemiaHistory",
        "hasFallHistory",
        "hasHypertension"
    ])
    
    # Check fatigue, low confidence, low activity, obesity, or complications
    confidence = safe_int(answers.get("confidenceLevel"))
    low_confidence = confidence < 5
    
    if (pa_status == "low" or 
        bmi_category == "obese" or 
        has_complications or 
        low_confidence or 
        answers.get("fatigue_reported") is True):
        return "plan_a_start_slowly"
        
    # 3. Default to Plan B
    return "plan_b_fitt"

def calculate_overall_risk(glycemic: str, physical_activity: str, sedentary: str, par_q_required: bool, complication_flags: Dict[str, bool]) -> str:
    # High risk markers
    has_complications = any(complication_flags.values())
    if par_q_required or glycemic in ["high", "red_flag"] or physical_activity == "low" or has_complications:
        return "high"
    # Moderate risk markers
    if glycemic == "moderate" or physical_activity == "moderate" or sedentary == "moderate_to_high":
        return "moderate"
    return "low"
