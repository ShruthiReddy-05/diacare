"""Module M2 -- Being Active (AADE7: Being Active).
Reference: ICMR 2018 Sec 6.3, 6.4.
Any complication or clearance flag from B3 overrides and downgrades this
plan before it is issued."""
from typing import Any, Dict, List
from utils import safe_int

RAMP_PROTOCOLS = {
    "low": [
        {"weeks": "1-2", "daily_minutes": "10-15", "note": "Beginner pace."},
        {"weeks": "3-4", "daily_minutes": "20-25", "note": "Add strength exercises."},
        {"weeks": "5-6", "daily_minutes": "30-45", "note": "Target 150 minutes a week."},
    ],
}

# "moderate"/"high" aren't a week-by-week ramp -- they're already active, so the
# plan is a single ongoing instruction, not a table with "weeks"/"minutes" columns.
ACTIVITY_GUIDANCE = {
    "moderate": "You're active 3-4 days a week. Add duration before intensity, working toward 150 minutes a week.",
    "high": "You're active 5 or more days a week. Maintain this, and add or increase resistance work.",
}


def classify_activity_category(activity_days_per_week: Any) -> str:
    days = safe_int(activity_days_per_week)
    if days <= 2:
        return "low"
    if days <= 4:
        return "moderate"
    return "high"


def build_activity_plan(activity_category: str, does_strength_yoga: bool, sedentary_work_flag: bool,
                         hypoglycemia_risk_flag: bool) -> Dict[str, Any]:
    plan = {
        "activity_category": activity_category,
        "ramp_protocol": RAMP_PROTOCOLS.get(activity_category),
        "activity_guidance": ACTIVITY_GUIDANCE.get(activity_category),
        "weekly_target": "About 150 minutes a week of aerobic activity, resistance training at least twice weekly, plus flexibility work.",
        "resistance_gap": not does_strength_yoga,
        "movement_break_rule": sedentary_work_flag,
        "post_meal_walk_emphasis": True,
        "glucose_check_addon": hypoglycemia_risk_flag,
    }
    if not does_strength_yoga:
        plan["resistance_exercise"] = {
            "activity_name": "Chair sit-to-stands, wall push-ups, resistance band rows",
            "duration": "10-15 repetitions",
            "frequency": "2-3 non-consecutive days per week",
        }
    return plan


def apply_clearance_filter(plan: Dict[str, Any], exercise_clearance_required: bool,
                             foot_risk_category: str) -> Dict[str, Any]:
    """Any complication/clearance flag from B3 downgrades the plan before issue."""
    if exercise_clearance_required:
        plan["activity_category"] = "clearance_pending"
        plan["ramp_protocol"] = None
        plan["activity_guidance"] = "Light activity only, 10-15 minutes a day, until medical clearance is obtained."
        plan["resistance_exercise"] = None
        plan["medical_clearance_required"] = True
    else:
        plan["medical_clearance_required"] = False

    if foot_risk_category in ("moderate", "high", "active_foot_disease"):
        plan["foot_precautions"] = [
            "Never walk barefoot, even indoors.",
            "Wear MCR or well-fitting covered footwear with dry socks.",
            "Walk only on flat, even ground.",
            "Check feet every night, including between the toes.",
        ]
        if foot_risk_category == "active_foot_disease":
            plan["activity_category"] = "non_weight_bearing_only"
            plan["ramp_protocol"] = None
            plan["activity_guidance"] = "Non-weight-bearing activity only, seated if needed, until healed. Refer to foot care within 24 hours."
            plan["resistance_exercise"] = None

    return plan


def compute_m2(answers: Dict[str, Any], sedentary_work_flag: bool = False,
               hypoglycemia_risk_flag: bool = False, exercise_clearance_required: bool = False,
               foot_risk_category: str = "low") -> Dict[str, Any]:
    activity_category = classify_activity_category(answers.get("activityDaysPerWeek"))
    does_strength_yoga = bool(answers.get("doesStrengthYogaStretching", False))
    plan = build_activity_plan(activity_category, does_strength_yoga, sedentary_work_flag, hypoglycemia_risk_flag)
    plan = apply_clearance_filter(plan, exercise_clearance_required, foot_risk_category)
    return plan
