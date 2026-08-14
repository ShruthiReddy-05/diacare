"""Assembles 'My Care Plan' (sections a-f + conditional/escalation blocks)
purely from stored BaselineProfile / ModuleOutcome data -- no network or LLM
call is ever involved. Every line is tagged with the answer keys it traces
back to, honoring the spec's design rule: content not supported by the
baseline assessment is withheld until the weekly check-in releases it."""
from typing import Any, Dict, List, Optional


ICMR_TARGET_TABLE = {
    "fasting_sugar": {"label": "Fasting sugar", "target": "80-110 mg/dl", "answer_key": "fastingSugar"},
    "post_meal_sugar": {"label": "2-hour post-meal sugar", "target": "120-140 mg/dl", "answer_key": "postMealSugar"},
    "hba1c": {"label": "HbA1c", "target": "Below 7%", "answer_key": "hba1c"},
    "blood_pressure": {"label": "Blood pressure", "target": "Below 130/80 mmHg", "answer_key": "bpSystolic,bpDiastolic"},
    "bmi": {"label": "BMI", "target": "20-23 kg/m2", "answer_key": "heightCm,weightKg"},
    "waist": {"label": "Waist", "target": "Below 90 cm (men) / 80 cm (women)", "answer_key": "waistCm"},
}

EMERGENCY_BULLETS_EN = [
    "Chest pain, or breathlessness at rest",
    "Severe giddiness, fainting or confusion",
    "Repeated vomiting, or you cannot keep fluids down",
    "Any wound, blackening, spreading redness or bad smell on your foot",
    "Sugar below 70 or above 400 mg/dl",
    "Sudden loss of vision, or passing much less urine",
]


def build_clinical_status(answers: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    rows = []
    for key, meta in ICMR_TARGET_TABLE.items():
        value = None
        if key == "fasting_sugar":
            value = answers.get("fastingSugar")
        elif key == "post_meal_sugar":
            value = answers.get("postMealSugar")
        elif key == "hba1c":
            value = answers.get("hba1c")
        elif key == "blood_pressure":
            s, d = answers.get("bpSystolic"), answers.get("bpDiastolic")
            value = f"{s}/{d} mmHg" if s and d else None
        elif key == "bmi":
            value = baseline.get("bmi")
        elif key == "waist":
            value = answers.get("waistCm")
        rows.append({"what": meta["label"], "last_value": value, "target": meta["target"], "trace": meta["answer_key"].split(",")})

    note = "Your doctor may set a different target for you. These are general targets."
    if baseline.get("age_band") == "60_and_above":
        note = "Because you are 60 or above, your doctor may set a higher, relaxed target for you."

    return {"rows": rows, "note": note, "trace": ["age"]}


def build_dietary_goals(m1_output: Dict[str, Any]) -> Dict[str, Any]:
    goals = m1_output.get("active_goals", [])
    return {
        "intro": "We picked only two, from what you told us. When these become easy, we will add the next two.",
        "goals": [{"text_en": g["text_en"], "trace": [g["goal_id"]]} for g in goals],
        "has_more_stored": len(m1_output.get("stored_goals", [])) > 0,
    }


def build_activity_plan(m2_output: Dict[str, Any]) -> Dict[str, Any]:
    plan = {
        "activity_category": m2_output.get("activity_category"),
        "weekly_target": m2_output.get("weekly_target"),
        "ramp_protocol": m2_output.get("ramp_protocol"),
        "activity_guidance": m2_output.get("activity_guidance"),
        "post_meal_walk_emphasis": m2_output.get("post_meal_walk_emphasis"),
        "trace": ["activityDaysPerWeek", "doesStrengthYogaStretching"],
    }
    if m2_output.get("resistance_exercise"):
        plan["resistance_exercise"] = m2_output["resistance_exercise"]
    if m2_output.get("movement_break_rule"):
        plan["movement_break_rule"] = "Stand and move for 3 minutes every 30-60 minutes (your work is seated)."
        plan["trace"].append("occupationType")
    if m2_output.get("foot_precautions"):
        plan["foot_precautions"] = m2_output["foot_precautions"]
        plan["trace"].append("hasNumbnessTingling")
    if m2_output.get("glucose_check_addon"):
        plan["glucose_check_note"] = "Check your sugar before and after activity until you know how your body responds. Carry sugar with you."
        plan["trace"].append("medications")
    if m2_output.get("medical_clearance_required"):
        plan["medical_clearance_note"] = "Please obtain medical clearance from your doctor before starting moderate-to-vigorous exercise."
    return plan


def build_sleep_and_stress(m4_output: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sleep_apnea_risk_flag": m4_output.get("sleep_apnea_risk_flag"),
        "coping_strategy": m4_output.get("coping_strategy"),
        "trace": ["sleepHours", "snoresLoudly", "daytimeSleepy", "feltLowOrLostInterest", "feltWorriedGuiltyTired"],
    }


def build_medicines_section(answers: Dict[str, Any], baseline: Dict[str, Any], m3_output: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "medications": answers.get("medicationTimings", []),
        "reminder_schedule": m3_output.get("reminder_schedule", []),
        "adherence_boilerplate": (
            "Keep taking your tablets even when your sugar is normal and you feel well. More than half of people "
            "with diabetes have no symptoms at all. Do not stop or change any dose yourself -- if something is "
            "troubling you, tell your doctor."
        ),
        "herbal_note": (
            "If you take any siddha, ayurvedic or herbal medicine, tell your doctor, because they can interact "
            "with your tablets." if baseline.get("herbal_use_flag") else None
        ),
        "trace": ["medicationTimings", "medications"],
    }


def build_monitoring_plan(m3_output: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    screening = baseline.get("screening_overdue") or {}
    overdue_items = []
    if screening.get("eye"):
        overdue_items.append("eye check")
    if screening.get("foot"):
        overdue_items.append("foot examination")
    if screening.get("renal"):
        overdue_items.append("urine test for protein")

    return {
        "monitoring_plan": m3_output.get("monitoring_plan"),
        "target_card": m3_output.get("target_card"),
        "screening_overdue": screening,
        "next_visit_script": (
            f"Doctor, it has been a while since my {', '.join(overdue_items)}. Can I have {'them' if len(overdue_items) > 1 else 'it'} done today?"
            if overdue_items else None
        ),
        "trace": ["lastEyeCheckDate", "lastFootCheckDate", "lastRenalTestDate", "statedTargetFasting", "statedTargetPostMeal"],
    }


def build_conditional_hypo_block(m4_output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not m4_output.get("hypo_recognition_needed"):
        return None
    return {
        "title": "If your sugar goes low",
        "protocol_text_en": m4_output.get("fifteen_fifteen_rule_text_en"),
        "escalation_note": "If these episodes keep happening, tell your doctor -- your tablets may need review.",
        "trace": ["hasHypoSymptoms"],
    }


def build_escalation_block() -> Dict[str, Any]:
    return {
        "title": "Stop and get help immediately if you have",
        "bullets": EMERGENCY_BULLETS_EN,
    }


def generate_care_plan(answers: Dict[str, Any], baseline: Dict[str, Any],
                        module_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """answers: raw baseline answer dict; baseline: BaselineProfile-shaped dict;
    module_outputs: {"M1": ..., "M2": ..., "M3": ..., "M4": ...}."""
    m1 = module_outputs.get("M1", {})
    m2 = module_outputs.get("M2", {})
    m3 = module_outputs.get("M3", {})
    m4 = module_outputs.get("M4", {})

    plan = {
        "disclaimer": "This plan supports the advice of your treating doctor. It does not replace it, and it never changes your medicine doses.",
        "clinical_status": build_clinical_status(answers, baseline),
        "dietary_goals": build_dietary_goals(m1),
        "activity_plan": build_activity_plan(m2),
        "sleep_and_stress": build_sleep_and_stress(m4),
        "medicines": build_medicines_section(answers, baseline, m3),
        "monitoring_plan": build_monitoring_plan(m3, baseline),
        "conditional_hypo_protocol": build_conditional_hypo_block(m4),
        "escalation": build_escalation_block(),
    }

    traceability = {}
    for section_key in ("clinical_status", "dietary_goals", "activity_plan", "sleep_and_stress", "medicines", "monitoring_plan"):
        section = plan[section_key]
        if isinstance(section, dict) and "trace" in section:
            traceability[section_key] = section["trace"]
    if plan["dietary_goals"].get("goals"):
        traceability["dietary_goals.goals"] = [g["trace"][0] for g in plan["dietary_goals"]["goals"]]
    if plan["conditional_hypo_protocol"]:
        traceability["conditional_hypo_protocol"] = plan["conditional_hypo_protocol"]["trace"]

    return plan, traceability
