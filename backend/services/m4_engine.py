"""Module M4 -- Healthy Coping & Problem Solving (AADE7: Healthy Coping, Problem Solving).
Reference: ICMR 2018 Sec 6.1, 6.2.4, 6.4, 8.1.1.
No diagnosis is ever made; the mood screen only flags a recommendation to
speak to a clinician or trusted person."""
from typing import Any, Dict
from utils import safe_float

FIFTEEN_FIFTEEN_RULE_EN = (
    "If you feel shaking, sweating, giddiness or sudden hunger: take sugar, glucose or sweets straight away. "
    "Wait 15 minutes and check again. If still low, take sugar once more. Then eat your next meal or a snack. "
    "Always carry sugar or glucose when you go out."
)


def classify_sleep_apnea_risk(sleep_hours: Any, snores_loudly: bool, daytime_sleepy: bool) -> bool:
    hours = safe_float(sleep_hours)
    return bool((hours and hours < 6) or (snores_loudly and daytime_sleepy))


def evaluate_mood_screen(felt_low_or_lost_interest: bool, felt_worried_guilty_tired: bool) -> bool:
    """Two-item mood screen. Positive result recommends clinician review --
    it is never itself a diagnosis."""
    return bool(felt_low_or_lost_interest or felt_worried_guilty_tired)


def select_coping_strategy(distress_flag: bool, poor_sleep: bool) -> str:
    if distress_flag:
        return "Reduce to a single active goal, celebrate small wins, and offer pranayama, gentle yoga, a long outdoor walk, or gardening."
    if poor_sleep:
        return "Sleep-hygiene guidance: fix one sleep time and keep to it, including on holidays."
    return "Reinforce current coping approach; no change needed."


def compute_m4(answers: Dict[str, Any]) -> Dict[str, Any]:
    has_hypo_symptoms = bool(answers.get("hasHypoSymptoms", False))
    poor_sleep = classify_sleep_apnea_risk(
        answers.get("sleepHours"), answers.get("snoresLoudly", False), answers.get("daytimeSleepy", False)
    )
    mood_positive = evaluate_mood_screen(
        answers.get("feltLowOrLostInterest", False), answers.get("feltWorriedGuiltyTired", False)
    )
    self_harm_expressed = bool(answers.get("expressedSelfHarm", False))
    distress_flag = mood_positive or bool(answers.get("diabetesDistressReported", False))

    return {
        "hypo_recognition_needed": has_hypo_symptoms,
        "fifteen_fifteen_rule_text_en": FIFTEEN_FIFTEEN_RULE_EN if has_hypo_symptoms else None,
        "sleep_apnea_risk_flag": poor_sleep,
        "mood_screen_positive": mood_positive,
        "self_harm_expressed": self_harm_expressed,
        "distress_flag": distress_flag,
        "reduce_active_goals": distress_flag,
        "coping_strategy": select_coping_strategy(distress_flag, poor_sleep),
    }
