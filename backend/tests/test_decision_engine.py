import pytest
from services.b1_engine import (
    classify_age_band, calculate_bmi, classify_bmi_asian, classify_waist_risk,
    calculate_ibw_kg, calculate_daily_energy_kcal, classify_occupational_activity, is_sedentary_work,
)
from services.b2_engine import (
    classify_glycemic_icmr, classify_duration_risk, classify_bp, salt_target_g,
    classify_regimen, classify_hypoglycemia_risk, classify_herbal_use, classify_follow_up_gap,
)
from services.b3_engine import (
    build_complication_profile, classify_foot_risk, classify_exercise_clearance, compute_overall_risk_tier,
)
from services.m1_engine import compute_m1
from services.m2_engine import classify_activity_category, compute_m2
from services.m3_engine import classify_adherence, classify_smbg_frequency, classify_target_knowledge, classify_barrier, compute_m3
from services.m4_engine import classify_sleep_apnea_risk, evaluate_mood_screen
from services.checkin_engine import evaluate_checkin
from services.safety_engine import check_safety_values, check_safety


def test_bmi_asian_cutoffs():
    assert calculate_bmi(170, 70) == 24.22
    assert calculate_bmi(0, 70) == 0.0

    assert classify_bmi_asian(17.5) == "underweight"
    assert classify_bmi_asian(20.0) == "normal"
    assert classify_bmi_asian(22.9) == "normal"
    assert classify_bmi_asian(23.0) == "overweight"
    assert classify_bmi_asian(24.9) == "overweight"
    assert classify_bmi_asian(25.0) == "obese"
    assert classify_bmi_asian(0.0) == "unknown"


def test_age_band():
    assert classify_age_band(59) == "under_60"
    assert classify_age_band(60) == "60_and_above"


def test_waist_risk():
    assert classify_waist_risk(91, "male") is True
    assert classify_waist_risk(90, "male") is False
    assert classify_waist_risk(81, "female") is True
    assert classify_waist_risk(80, "female") is False


def test_ibw_and_daily_energy():
    assert calculate_ibw_kg(170) == 63.0
    assert calculate_daily_energy_kcal(63.0) == 1575.0


def test_occupational_activity_and_sedentary_flag():
    assert classify_occupational_activity("sitting") == "sitting"
    assert classify_occupational_activity("heavy") == "heavy"
    assert is_sedentary_work("sitting") is True
    assert is_sedentary_work("standing") is False


def test_glycemic_icmr_bands():
    assert classify_glycemic_icmr(hba1c=6.5) == "target"
    assert classify_glycemic_icmr(hba1c=7.5) == "satisfactory"
    assert classify_glycemic_icmr(hba1c=8.4) == "unsatisfactory"
    assert classify_glycemic_icmr(fpg=100) == "target"
    assert classify_glycemic_icmr(fpg=120) == "satisfactory"
    assert classify_glycemic_icmr(fpg=200) == "unsatisfactory"
    assert classify_glycemic_icmr(ppg=130) == "target"
    assert classify_glycemic_icmr() == "unknown"


def test_bp_category_and_salt_target():
    assert classify_bp(120, 78) == "target"
    assert classify_bp(135, 82) == "elevated"
    assert classify_bp(142, 88) == "high"
    assert salt_target_g("high") == 3.0
    assert salt_target_g("target") == 5.0


def test_regimen_and_hypoglycemia_risk():
    assert classify_regimen("Metformin 500mg") == "metformin_only"
    assert classify_regimen("Glimepiride and metformin") == "sulfonylurea"
    assert classify_regimen("Insulin (Lantus)") == "insulin"
    assert classify_hypoglycemia_risk("insulin") is True
    assert classify_hypoglycemia_risk("sulfonylurea") is True
    assert classify_hypoglycemia_risk("metformin_only") is False


def test_herbal_use_and_duration_risk():
    assert classify_herbal_use("Metformin and some siddha medicine") is True
    assert classify_herbal_use("Metformin only") is False
    assert classify_duration_risk(6) is True
    assert classify_duration_risk(5) is False


def test_b3_complication_and_foot_risk():
    profile = build_complication_profile({"hasHeartCondition": True, "hasKidneyDiseaseOrSwelling": True})
    assert profile["cad"] is True
    assert profile["nephropathy"] is True
    assert profile["neuropathy"] is False

    assert classify_foot_risk(has_wound_or_ulcer=True, has_numbness_tingling=False) == "active_foot_disease"
    assert classify_foot_risk(has_wound_or_ulcer=False, has_numbness_tingling=True) == "moderate"
    assert classify_foot_risk(has_wound_or_ulcer=False, has_numbness_tingling=False) == "low"

    assert classify_exercise_clearance({"cad": True, "nephropathy": False}) is True
    assert classify_exercise_clearance({"cad": False, "nephropathy": False}) is False


def test_overall_risk_tier():
    assert compute_overall_risk_tier(True, "low", {}, "target") == "red"
    assert compute_overall_risk_tier(False, "active_foot_disease", {}, "target") == "red"
    assert compute_overall_risk_tier(False, "moderate", {}, "target") == "amber"
    assert compute_overall_risk_tier(False, "low", {"neuropathy": True}, "target") == "amber"
    assert compute_overall_risk_tier(False, "low", {}, "unsatisfactory") == "amber"
    assert compute_overall_risk_tier(False, "low", {}, "target") == "green"


def test_m1_selects_top_two_goals():
    answers = {
        "riceCupsPerMeal": 3, "eatsMilletsWholeWheat": False,
        "friedSweetFrequencyPerWeek": 4, "vegetablePortionsPerDay": 1,
        "addsExtraSalt": True, "eatsPicklesOrPackagedSnacksOften": True,
        "mealsPerDay": 3,
    }
    result = compute_m1(answers, bp_category="high", hypoglycemia_risk_flag=True)
    assert len(result["active_goals"]) == 2
    assert len(result["stored_goals"]) > 0
    # highest gap-score candidates come first
    assert result["candidate_goals"][0]["gap_score"] >= result["candidate_goals"][1]["gap_score"]


def test_m1_nephropathy_skips_salt_goal():
    answers = {"addsExtraSalt": True, "eatsPicklesOrPackagedSnacksOften": True}
    result = compute_m1(answers, bp_category="high", nephropathy=True)
    goal_ids = [g["goal_id"] for g in result["candidate_goals"]]
    assert "reduce_salt" not in goal_ids


def test_m2_activity_category_and_clearance_override():
    assert classify_activity_category(1) == "low"
    assert classify_activity_category(3) == "moderate"
    assert classify_activity_category(6) == "high"

    plan = compute_m2({"activityDaysPerWeek": 5, "doesStrengthYogaStretching": True}, exercise_clearance_required=True)
    assert plan["medical_clearance_required"] is True
    assert plan["activity_category"] == "clearance_pending"

    foot_plan = compute_m2({"activityDaysPerWeek": 5}, foot_risk_category="active_foot_disease")
    assert foot_plan["activity_category"] == "non_weight_bearing_only"


def test_m3_adherence_and_smbg():
    assert classify_adherence(0) == "full"
    assert classify_adherence(2) == "partial"
    assert classify_adherence(3) == "poor"
    assert classify_smbg_frequency("insulin", False, "target") == "intensified"
    assert classify_smbg_frequency("metformin_only", False, "unsatisfactory") == "frequent"
    assert classify_smbg_frequency("metformin_only", False, "target") == "standard"


def test_m3_target_knowledge_is_graded_not_self_reported():
    # correct on both fasting (80-110) and post-meal (120-140)
    assert classify_target_knowledge(100, 130) is True
    # fasting out of range
    assert classify_target_knowledge(150, 130) is False
    # post-meal out of range
    assert classify_target_knowledge(100, 200) is False
    # missing / unanswered
    assert classify_target_knowledge(None, None) is False

    correct = compute_m3({"statedTargetFasting": 100, "statedTargetPostMeal": 130})
    assert correct["knowledge_gap"] is False
    wrong = compute_m3({"statedTargetFasting": 90, "statedTargetPostMeal": 220})
    assert wrong["knowledge_gap"] is True


def test_m3_barrier_is_a_controlled_value_not_guessed():
    assert classify_barrier("cost") == "cost"
    assert classify_barrier("forgetfulness") == "forgetfulness"
    assert classify_barrier("other") == "unknown"
    assert classify_barrier(None) == "unknown"

    poor_adherence = compute_m3({"dosesMissedLast7Days": 4, "missedDoseReason": "side_effect"})
    assert poor_adherence["rerun_barrier_assessment"] is True
    assert poor_adherence["barrier"] == "side_effect"


def test_m4_sleep_apnea_and_mood_screen():
    assert classify_sleep_apnea_risk(5, False, False) is True
    assert classify_sleep_apnea_risk(7, True, True) is True
    assert classify_sleep_apnea_risk(7, False, False) is False
    assert evaluate_mood_screen(True, False) is True
    assert evaluate_mood_screen(False, False) is False


def test_checkin_progression_rules():
    answers = {
        "q1_activity_days": 5, "q2_food_goal_days": 1, "q3_medication_days": 3,
        "q4_foot_care_days": 6, "q6_stress_0_10": 8, "q7_sleep_0_10": 3,
    }
    evaluation = evaluate_checkin(answers, neuropathy_flag=True)
    assert evaluation["activity_progression"] == "increase_duration"
    assert evaluation["food_progression"] == "renegotiate_smaller_goal"
    assert evaluation["medication"]["rerun_m3_barrier_assessment"] is True
    assert evaluation["foot_care"]["reinforce"] is False
    assert evaluation["stress"]["deliver_coping_content"] is True
    assert evaluation["sleep"]["deliver_sleep_hygiene_content"] is True
    assert evaluation["week_is_poor"] is True
    assert evaluation["consecutive_poor_weeks"] == 1
    assert evaluation["reassessment_triggered"] is False


def test_checkin_two_consecutive_poor_weeks_triggers_reassessment():
    poor_answers = {
        "q1_activity_days": 0, "q2_food_goal_days": 0, "q3_medication_days": 0,
        "q4_foot_care_days": 0, "q6_stress_0_10": 5, "q7_sleep_0_10": 5,
    }
    evaluation = evaluate_checkin(poor_answers, previous_consecutive_poor_weeks=1)
    assert evaluation["consecutive_poor_weeks"] == 2
    assert evaluation["reassessment_triggered"] is True


def test_safety_engine_red_flags():
    triggered = check_safety_values({"chestPain": True, "sugarReading": 65})
    assert "chest_pain" in triggered
    assert "sugar_below_70" in triggered

    triggered_high = check_safety_values({"sugarReading": 420})
    assert "sugar_above_400" in triggered_high

    assert check_safety_values({}) == []
    assert check_safety({}, free_text="I have chest pain and can't breathe") == ["chest_pain", "breathlessness_at_rest"]
