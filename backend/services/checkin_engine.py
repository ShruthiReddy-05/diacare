"""Module C -- weekly check-in decision logic (8 items -> per-domain
progression/regression, triggered content release, and the two-consecutive-
poor-weeks full-reassessment trigger).
Reference: ICMR 2018 Sec 1.6, 5.1, 6.2.3, 8.1.2."""
from typing import Any, Dict

GOOD_DAYS_THRESHOLD = 5
POOR_DAYS_THRESHOLD = 2
STRESS_HIGH_THRESHOLD = 7
SLEEP_LOW_THRESHOLD = 4
POOR_WEEKS_FOR_REASSESSMENT = 2


def classify_activity_progression(days: int) -> str:
    if days >= GOOD_DAYS_THRESHOLD:
        return "increase_duration"
    if days > POOR_DAYS_THRESHOLD:
        return "hold_problem_solve_barrier"
    return "simplify_to_one_goal"


def classify_food_progression(days: int) -> str:
    if days >= GOOD_DAYS_THRESHOLD:
        return "release_next_stored_goal"
    if days > POOR_DAYS_THRESHOLD:
        return "hold"
    return "renegotiate_smaller_goal"


def classify_medication_progression(days: int) -> Dict[str, Any]:
    """Fewer than 5 of 7 days: re-run the M3 barrier assessment rather than
    repeating reminders."""
    return {"rerun_m3_barrier_assessment": days < GOOD_DAYS_THRESHOLD}


def classify_foot_care_progression(days: int, neuropathy_flag: bool) -> Dict[str, Any]:
    reinforce = days < GOOD_DAYS_THRESHOLD
    return {
        "reinforce": reinforce,
        "raise_priority": bool(reinforce and neuropathy_flag),
        "repeat_daily_inspection_instruction": bool(reinforce and neuropathy_flag),
    }


def classify_stress_response(stress_0_10: int) -> Dict[str, Any]:
    high = stress_0_10 >= STRESS_HIGH_THRESHOLD
    return {"deliver_coping_content": high, "reduce_active_goals": high}


def classify_sleep_response(sleep_0_10: int) -> Dict[str, Any]:
    low = sleep_0_10 <= SLEEP_LOW_THRESHOLD
    return {"deliver_sleep_hygiene_content": low, "lower_exercise_intensity_this_week": low}


def determine_triggered_content(fever_or_vomiting_reported: bool, upcoming_function_or_fasting: bool) -> Dict[str, bool]:
    return {
        "sick_day": bool(fever_or_vomiting_reported),
        "festival_fasting": bool(upcoming_function_or_fasting),
    }


def is_week_poor(activity_progression: str, food_progression: str, medication: Dict[str, Any],
                  foot_care: Dict[str, Any]) -> bool:
    """A week counts as 'poor' if any domain regressed to its lowest band."""
    return (
        activity_progression == "simplify_to_one_goal"
        or food_progression == "renegotiate_smaller_goal"
        or medication["rerun_m3_barrier_assessment"]
        or foot_care["reinforce"]
    )


def evaluate_checkin(answers: Dict[str, Any], neuropathy_flag: bool = False,
                      previous_consecutive_poor_weeks: int = 0) -> Dict[str, Any]:
    activity_progression = classify_activity_progression(answers["q1_activity_days"])
    food_progression = classify_food_progression(answers["q2_food_goal_days"])
    medication = classify_medication_progression(answers["q3_medication_days"])
    foot_care = classify_foot_care_progression(answers["q4_foot_care_days"], neuropathy_flag)
    stress = classify_stress_response(answers["q6_stress_0_10"])
    sleep = classify_sleep_response(answers["q7_sleep_0_10"])
    triggered_content = determine_triggered_content(
        answers.get("fever_or_vomiting_reported", False), answers.get("upcoming_function_or_fasting", False)
    )

    week_poor = is_week_poor(activity_progression, food_progression, medication, foot_care)
    new_streak = (previous_consecutive_poor_weeks + 1) if week_poor else 0
    reassessment_triggered = new_streak >= POOR_WEEKS_FOR_REASSESSMENT

    return {
        "activity_progression": activity_progression,
        "food_progression": food_progression,
        "medication": medication,
        "foot_care": foot_care,
        "stress": stress,
        "sleep": sleep,
        "triggered_content": triggered_content,
        "new_foot_problem_routes_to_safety": bool(answers.get("q5_new_foot_problem", False)),
        "week_is_poor": week_poor,
        "consecutive_poor_weeks": new_streak,
        "reassessment_triggered": reassessment_triggered,
    }
