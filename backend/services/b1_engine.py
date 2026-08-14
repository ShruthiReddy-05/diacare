"""Module B1 -- basic profile. Deterministic derivations only.
Reference: ICMR 2018 Sec 4.1, 6.2.1, 10.3."""
from typing import Any, Dict, Optional
from utils import safe_float, safe_int


def classify_age_band(age: Any) -> str:
    return "60_and_above" if safe_int(age) >= 60 else "under_60"


def calculate_bmi(height_cm: Optional[float], weight_kg: Optional[float]) -> float:
    h = safe_float(height_cm)
    w = safe_float(weight_kg)
    if not h or not w or h <= 0:
        return 0.0
    return round(w / ((h / 100) ** 2), 2)


def classify_bmi_asian(bmi: float) -> str:
    """Asian-Indian BMI cut-offs: overweight >=23, obese >=25."""
    if bmi <= 0:
        return "unknown"
    if bmi < 18.5:
        return "underweight"
    if bmi < 23:
        return "normal"
    if bmi < 25:
        return "overweight"
    return "obese"


def classify_waist_risk(waist_cm: Any, sex: str) -> bool:
    w = safe_float(waist_cm)
    if not w:
        return False
    sex_norm = str(sex or "").strip().lower()
    if sex_norm in ("m", "male"):
        return w > 90
    if sex_norm in ("f", "female"):
        return w > 80
    return False


def calculate_ibw_kg(height_cm: Any) -> float:
    h = safe_float(height_cm)
    if h <= 0:
        return 0.0
    return round((h - 100) * 0.9, 2)


def calculate_daily_energy_kcal(ibw_kg: float) -> float:
    if ibw_kg <= 0:
        return 0.0
    return round(25 * ibw_kg, 0)


def classify_occupational_activity(occupation_type: Any) -> str:
    val = str(occupation_type or "").strip().lower()
    if val in ("sitting", "seated", "desk"):
        return "sitting"
    if val in ("standing",):
        return "standing"
    if val in ("heavy", "manual", "labour", "labor"):
        return "heavy"
    return "sitting"


def is_sedentary_work(occupational_activity_level: str) -> bool:
    return occupational_activity_level == "sitting"


def compute_b1(answers: Dict[str, Any]) -> Dict[str, Any]:
    bmi = calculate_bmi(answers.get("heightCm"), answers.get("weightKg"))
    ibw = calculate_ibw_kg(answers.get("heightCm"))
    occupational_activity_level = classify_occupational_activity(answers.get("occupationType"))
    return {
        "age_band": classify_age_band(answers.get("age")),
        "bmi": bmi,
        "bmi_category": classify_bmi_asian(bmi),
        "waist_risk": classify_waist_risk(answers.get("waistCm"), answers.get("sex")),
        "ideal_body_weight_kg": ibw,
        "daily_energy_kcal": calculate_daily_energy_kcal(ibw),
        "occupational_activity_level": occupational_activity_level,
        "sedentary_work_flag": is_sedentary_work(occupational_activity_level),
    }
