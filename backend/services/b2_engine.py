"""Module B2 -- diabetes profile. Deterministic derivations only.
Reference: ICMR 2018 Sec 4.1, 5.1, 5.3, 7.1.1, 7.1.2, 7.1.11, 7.2.5-7.2.7, 8.5.3, 10.1."""
from datetime import date
from typing import Any, Dict, Optional
from utils import safe_float

SULFONYLUREAS = ["glimepiride", "gliclazide", "glipizide", "sulfonylurea", "amaryl", "diamicron"]
INSULIN_KEYWORDS = ["insulin", "lantus", "mixtard", "actrapid", "humalog", "novorapid", "glargine"]
HERBAL_KEYWORDS = ["siddha", "ayurved", "herbal", "kabasura", "nilavembu", "homeopath"]


def classify_glycemic_icmr(hba1c: Any = None, fpg: Any = None, ppg: Any = None) -> str:
    """target / satisfactory / unsatisfactory, against ICMR bands."""
    h = safe_float(hba1c) if hba1c not in (None, "") else None
    f = safe_float(fpg) if fpg not in (None, "") else None
    p = safe_float(ppg) if ppg not in (None, "") else None

    if h:
        if h < 7.0:
            return "target"
        if h < 8.0:
            return "satisfactory"
        return "unsatisfactory"
    if f:
        if 80 <= f <= 110:
            return "target"
        if f <= 125:
            return "satisfactory"
        return "unsatisfactory"
    if p:
        if 120 <= p <= 140:
            return "target"
        if p <= 180:
            return "satisfactory"
        return "unsatisfactory"
    return "unknown"


def classify_duration_risk(duration_years: Any) -> bool:
    return safe_float(duration_years) > 5


def classify_bp(systolic: Any, diastolic: Any) -> str:
    s = safe_float(systolic)
    d = safe_float(diastolic)
    if not s and not d:
        return "unknown"
    if s >= 140 or d >= 90:
        return "high"
    if s >= 130 or d >= 80:
        return "elevated"
    return "target"


def salt_target_g(bp_category: str) -> float:
    return 3.0 if bp_category == "high" else 5.0


def classify_regimen(medications_text: Any) -> str:
    text = str(medications_text or "").lower()
    if any(kw in text for kw in INSULIN_KEYWORDS):
        return "insulin"
    if any(kw in text for kw in SULFONYLUREAS):
        return "sulfonylurea"
    return "metformin_only"


def classify_hypoglycemia_risk(regimen_class: str) -> bool:
    return regimen_class in ("insulin", "sulfonylurea")


def classify_herbal_use(medications_text: Any) -> bool:
    text = str(medications_text or "").lower()
    return any(kw in text for kw in HERBAL_KEYWORDS)


def _days_since(value: Any, today: Optional[date] = None) -> Optional[int]:
    if not value:
        return None
    today = today or date.today()
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value[:10])
        except ValueError:
            return None
    if isinstance(value, date):
        return (today - value).days
    return None


def classify_follow_up_gap(last_visit_date: Any, today: Optional[date] = None) -> bool:
    days = _days_since(last_visit_date, today)
    return days is not None and days > 90


def classify_screening_overdue(eye_check_date: Any, foot_check_date: Any, renal_test_date: Any,
                                 today: Optional[date] = None) -> Dict[str, bool]:
    def overdue(d):
        days = _days_since(d, today)
        return days is None or days > 365

    return {
        "eye": overdue(eye_check_date),
        "foot": overdue(foot_check_date),
        "renal": overdue(renal_test_date),
    }


def compute_b2(answers: Dict[str, Any]) -> Dict[str, Any]:
    bp_category = classify_bp(answers.get("bpSystolic"), answers.get("bpDiastolic"))
    regimen_class = classify_regimen(answers.get("medications"))
    return {
        "glycemic_category": classify_glycemic_icmr(
            answers.get("hba1c"), answers.get("fastingSugar"), answers.get("postMealSugar")
        ),
        "duration_risk_flag": classify_duration_risk(answers.get("durationYears")),
        "bp_category": bp_category,
        "salt_target_g": salt_target_g(bp_category),
        "regimen_class": regimen_class,
        "hypoglycemia_risk_flag": classify_hypoglycemia_risk(regimen_class),
        "herbal_use_flag": classify_herbal_use(answers.get("medications")),
        "follow_up_gap_flag": classify_follow_up_gap(answers.get("lastVisitDate")),
        "screening_overdue": classify_screening_overdue(
            answers.get("lastEyeCheckDate"), answers.get("lastFootCheckDate"), answers.get("lastRenalTestDate")
        ),
    }
