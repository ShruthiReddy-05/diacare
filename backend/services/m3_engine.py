"""Module M3 -- Taking Medication & Monitoring (AADE7: Taking Medication, Monitoring).
Reference: ICMR 2018 Sec 3.2, 4.1, 5.1, 5.2, 7.1.9.
NOTE: no dose is ever added, changed, doubled or stopped by the chatbot."""
from typing import Any, Dict, List
from utils import safe_int

ICMR_TARGETS = {
    "fasting_sugar": "80-110 mg/dl",
    "post_meal_sugar": "120-140 mg/dl",
    "hba1c": "Below 7%",
}

FASTING_TARGET_RANGE = (80, 110)
POST_MEAL_TARGET_RANGE = (120, 140)

VALID_BARRIERS = {"forgetfulness", "cost", "side_effect", "health_belief"}


def classify_adherence(doses_missed_last_7_days: Any) -> str:
    missed = safe_int(doses_missed_last_7_days)
    if missed == 0:
        return "full"
    if missed <= 2:
        return "partial"
    return "poor"


def build_reminder_schedule(medication_timings: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Reminders anchored to the actual dose times captured in B2, not
    generic slots."""
    schedule = []
    for entry in (medication_timings or []):
        name = entry.get("name")
        timing = entry.get("timing")
        if name and timing:
            schedule.append({"label": name, "time_of_day": timing})
    return schedule


def classify_smbg_frequency(regimen_class: str, hypoglycemia_risk_flag: bool, glycemic_category: str) -> str:
    """Intensify SMBG if on insulin, prone to recurrent hypoglycaemia, or
    hypoglycaemia unawareness / acute illness."""
    if regimen_class == "insulin" or hypoglycemia_risk_flag:
        return "intensified"
    if glycemic_category == "unsatisfactory":
        return "frequent"
    return "standard"


def build_monitoring_plan(glycemic_category: str, smbg_frequency: str) -> Dict[str, str]:
    hba1c_interval = "3 months" if glycemic_category == "unsatisfactory" else "6 months"
    return {
        "fasting_post_meal_sugar": "At least once a month, more often if out of range" if smbg_frequency == "standard"
            else "Weekly" if smbg_frequency == "frequent" else "Before and after activity, and as advised",
        "hba1c": f"Every {hba1c_interval} until at target",
    }


def classify_barrier(missed_reason_value: Any) -> str:
    """missed_reason_value is a controlled single_choice answer (one of
    VALID_BARRIERS, or "other"/blank) -- no keyword guessing needed."""
    value = str(missed_reason_value or "").strip()
    return value if value in VALID_BARRIERS else "unknown"


def classify_target_knowledge(stated_fasting: Any, stated_post_meal: Any) -> bool:
    """The patient states their own understanding of fasting/post-meal
    targets; this grades it against the real ICMR ranges rather than
    trusting a self-report of "yes I know it"."""
    fasting = safe_int(stated_fasting)
    post_meal = safe_int(stated_post_meal)
    fasting_ok = FASTING_TARGET_RANGE[0] <= fasting <= FASTING_TARGET_RANGE[1]
    post_meal_ok = POST_MEAL_TARGET_RANGE[0] <= post_meal <= POST_MEAL_TARGET_RANGE[1]
    return fasting_ok and post_meal_ok


def build_target_card(age_band: str) -> Dict[str, Any]:
    card = dict(ICMR_TARGETS)
    note = "Your doctor may set a different target for you. These are general targets."
    if age_band == "60_and_above":
        note = "Because you are 60 or above, your doctor may set a higher, relaxed target for you."
    return {"targets": card, "note": note}


def compute_m3(answers: Dict[str, Any], regimen_class: str = "metformin_only",
               hypoglycemia_risk_flag: bool = False, glycemic_category: str = "unknown",
               age_band: str = "under_60") -> Dict[str, Any]:
    adherence = classify_adherence(answers.get("dosesMissedLast7Days"))
    smbg_frequency = classify_smbg_frequency(regimen_class, hypoglycemia_risk_flag, glycemic_category)
    target_answer_correct = classify_target_knowledge(
        answers.get("statedTargetFasting"), answers.get("statedTargetPostMeal")
    )

    result = {
        "adherence": adherence,
        "reminder_schedule": build_reminder_schedule(answers.get("medicationTimings", [])),
        "smbg_frequency": smbg_frequency,
        "monitoring_plan": build_monitoring_plan(glycemic_category, smbg_frequency),
        "knowledge_gap": not target_answer_correct,
        "target_card": build_target_card(age_band),
    }

    if adherence == "poor":
        result["barrier"] = classify_barrier(answers.get("missedDoseReason"))
        result["rerun_barrier_assessment"] = True
    else:
        result["rerun_barrier_assessment"] = False

    return result
