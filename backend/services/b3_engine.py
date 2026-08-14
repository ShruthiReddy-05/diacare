"""Module B3 -- risk & complication screening. Deterministic derivations only.
Reference: ICMR 2018 Sec 6.2.4, 6.3, 8.3, 8.5, 8.6, 8.7.3, 8.7.4."""
from typing import Any, Dict


def build_complication_profile(answers: Dict[str, Any]) -> Dict[str, bool]:
    return {
        "neuropathy": bool(answers.get("hasNumbnessTingling", False)),
        "retinopathy": bool(answers.get("hasEyeDiseaseOrLaser", False)),
        "nephropathy": bool(answers.get("hasKidneyDiseaseOrSwelling", False)),
        "cad": bool(answers.get("hasHeartCondition", False)),
    }


def classify_foot_risk(has_wound_or_ulcer: bool, has_numbness_tingling: bool) -> str:
    if has_wound_or_ulcer:
        return "active_foot_disease"
    if has_numbness_tingling:
        return "moderate"
    return "low"


def classify_exercise_clearance(complication_profile: Dict[str, bool]) -> bool:
    """Known heart condition or nephropathy -> medical clearance required before
    moderate/vigorous activity or before increasing activity."""
    return bool(complication_profile.get("cad") or complication_profile.get("nephropathy"))


def compute_overall_risk_tier(exercise_clearance_required: bool, foot_risk_category: str,
                                complication_profile: Dict[str, bool], glycemic_category: str) -> str:
    """red = clearance pending, light activity and safety content only;
    amber = modified plan; green = full plan."""
    if exercise_clearance_required or foot_risk_category == "active_foot_disease":
        return "red"
    has_any_complication = any(complication_profile.values())
    if has_any_complication or foot_risk_category == "moderate" or glycemic_category == "unsatisfactory":
        return "amber"
    return "green"


def compute_b3(answers: Dict[str, Any], glycemic_category: str = "unknown") -> Dict[str, Any]:
    complication_profile = build_complication_profile(answers)
    has_wound = bool(answers.get("hasFootWoundOrUlcer", False))
    has_numbness = bool(answers.get("hasNumbnessTingling", False))
    foot_risk_category = classify_foot_risk(has_wound, has_numbness)
    exercise_clearance_required = classify_exercise_clearance(complication_profile)
    return {
        "complication_profile": complication_profile,
        "foot_risk_category": foot_risk_category,
        "exercise_clearance_required": exercise_clearance_required,
        "tobacco_flag": bool(answers.get("usesTobacco", False)),
        "alcohol_flag": bool(answers.get("drinksAlcohol", False)),
        "overall_risk_tier": compute_overall_risk_tier(
            exercise_clearance_required, foot_risk_category, complication_profile, glycemic_category
        ),
    }
