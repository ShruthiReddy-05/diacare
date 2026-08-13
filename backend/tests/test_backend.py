import pytest
from services.risk_engine import (
    calculate_bmi, classify_bmi, classify_glycemic,
    calculate_met_min_week, classify_physical_activity, classify_sedentary,
    evaluate_par_q, build_complication_flags,
    classify_hypoglycemia_risk, select_plan_type,
    calculate_overall_risk
)
from services.prescription_validator import validate_and_sanitize_prescription

def test_bmi_calculation_and_classification():
    assert calculate_bmi(170, 70) == 24.22
    assert calculate_bmi(0, 70) == 0.0
    assert calculate_bmi(180, None) == 0.0
    
    assert classify_bmi(17.5) == "underweight"
    assert classify_bmi(22.0) == "normal"
    assert classify_bmi(22.9) == "normal"
    assert classify_bmi(23.0) == "overweight"
    assert classify_bmi(27.0) == "overweight"
    assert classify_bmi(27.4) == "overweight"
    assert classify_bmi(27.5) == "obese"
    assert classify_bmi(32.5) == "obese"
    assert classify_bmi(0.0) == "unknown"

def test_glycemic_classification():
    # Fasting sugar > 300 path
    assert classify_glycemic(fasting_sugar=320) == "red_flag"
    
    # HbA1c path
    assert classify_glycemic(hba1c=6.5) == "good"
    assert classify_glycemic(hba1c=8.0) == "moderate"
    assert classify_glycemic(hba1c=9.5) == "high"
    
    # Fasting sugar path
    assert classify_glycemic(fasting_sugar=110) == "good"
    assert classify_glycemic(fasting_sugar=150) == "moderate"
    assert classify_glycemic(fasting_sugar=200) == "high"
    assert classify_glycemic() == "unknown"

def test_calculate_met_min_week():
    # No activity
    assert calculate_met_min_week({}) == 0.0

    # Walking only: 5 days x 30 min x 3.3 MET = 495
    assert calculate_met_min_week({"walkingDays": 5, "walkingMinutes": 30}) == 495.0

    # Moderate only: 3 days x 20 min x 4.0 MET = 240
    assert calculate_met_min_week({"moderateDays": 3, "moderateMinutes": 20}) == 240.0

    # Vigorous only: 2 days x 45 min x 8.0 MET = 720
    assert calculate_met_min_week({"vigorousDays": 2, "vigorousMinutes": 45}) == 720.0

    # Combined: 495 + 240 + 720 = 1455
    combined = calculate_met_min_week({
        "walkingDays": 5, "walkingMinutes": 30,
        "moderateDays": 3, "moderateMinutes": 20,
        "vigorousDays": 2, "vigorousMinutes": 45
    })
    assert combined == 1455.0

def test_physical_activity_classification():
    # IPAQ MET-min/week thresholds
    assert classify_physical_activity(3500) == "adequate"
    assert classify_physical_activity(3000) == "adequate"
    assert classify_physical_activity(1500) == "moderate"
    assert classify_physical_activity(600) == "moderate"
    assert classify_physical_activity(300) == "low"
    assert classify_physical_activity(0) == "low"

def test_sedentary_classification():
    assert classify_sedentary(3.5) == "low"
    assert classify_sedentary(4.0) == "moderate_to_high"
    assert classify_sedentary(8.0) == "moderate_to_high"

def test_par_q_evaluation():
    answers_no = {
        "parqHeartCondition": False,
        "parqChestPainActivity": False,
        "parqChestPainRest": False,
        "parqDizziness": False,
        "parqBoneJoint": False,
        "parqDrugs": False,
        "parqOtherReason": False,
    }
    assert evaluate_par_q(answers_no) is False
    
    answers_yes = dict(answers_no)
    answers_yes["parqDizziness"] = True
    assert evaluate_par_q(answers_yes) is True

def test_complication_flags():
    answers = {
        "hasHypertension": True,
        "hasNeuropathySymptoms": False,
        "hasEyeDisease": True,
    }
    flags = build_complication_flags(answers)
    assert flags["hasHypertension"] is True
    assert flags["hasNeuropathySymptoms"] is False
    assert flags["hasEyeDisease"] is True
    assert flags["hasKidneyDisease"] is False

def test_hypoglycemia_risk():
    assert classify_hypoglycemia_risk({"usesInsulin": True}) == "high"
    assert classify_hypoglycemia_risk({"hasExerciseHypoglycemiaHistory": True}) == "high"
    assert classify_hypoglycemia_risk({"medications": "Glimepiride and metformin"}) == "moderate"
    assert classify_hypoglycemia_risk({"medications": "Metformin only"}) == "low"

def test_plan_type_selection():
    # 1. Medical Clearance - PAR-Q
    risk_clearance = {
        "par_q_clearance_required": True,
        "complication_flags": {},
        "glycemic": "good",
        "bmi_category": "normal",
        "physical_activity": "adequate"
    }
    assert select_plan_type(risk_clearance, {}) == "medical_clearance_required"
    
    # 2. Medical Clearance - HbA1c ≥ 8%
    risk_good = {
        "par_q_clearance_required": False,
        "complication_flags": {},
        "glycemic": "good",
        "bmi_category": "normal",
        "physical_activity": "adequate"
    }
    assert select_plan_type(risk_good, {"hba1c": 8.0}) == "medical_clearance_required"
    assert select_plan_type(risk_good, {"hba1c": 8.5}) == "medical_clearance_required"
    assert select_plan_type(risk_good, {"hba1c": 7.9}) != "medical_clearance_required"
    
    # 3. Plan A - Low Activity (MET < 600)
    risk_plan_a_low_act = {
        "par_q_clearance_required": False,
        "complication_flags": {},
        "glycemic": "good",
        "bmi_category": "normal",
        "physical_activity": "low"
    }
    assert select_plan_type(risk_plan_a_low_act, {}) == "plan_a_start_slowly"
    
    # 4. Plan A - Obesity
    risk_plan_a_obese = {
        "par_q_clearance_required": False,
        "complication_flags": {},
        "glycemic": "good",
        "bmi_category": "obese",
        "physical_activity": "adequate"
    }
    assert select_plan_type(risk_plan_a_obese, {}) == "plan_a_start_slowly"
    
    # 5. Plan B - FITT
    risk_plan_b = {
        "par_q_clearance_required": False,
        "complication_flags": {
            "hasNeuropathySymptoms": False,
            "hasEyeDisease": False,
            "hasKidneyDisease": False,
            "hasFootWoundOrUlcer": False,
            "hasExerciseHypoglycemiaHistory": False,
            "hasFallHistory": False,
            "hasHypertension": False,
        },
        "glycemic": "good",
        "bmi_category": "normal",
        "physical_activity": "adequate"
    }
    assert select_plan_type(risk_plan_b, {}) == "plan_b_fitt"

def test_prescription_validator():
    # Test reduction of vigorous exercises when contraindicated
    mock_prescription = {
        "planType": "plan_b_fitt",
        "activityPlan": [
            {
                "activityName": "Brisk jogging",
                "intensity": "vigorous",
                "duration": "30 minutes",
                "frequency": "5 days per week",
                "progressionRule": "Increase duration",
                "safetyReason": "standard",
                "ragSourceIds": [],
                "contraindicationChecksApplied": []
            }
        ],
        "simpleActivities": [],
        "strengthExercises": [],
        "personalizedTips": [],
        "safetyWarnings": []
    }
    
    # Contraindicated because of eye disease
    risk_result = {
        "par_q_clearance_required": False,
        "glycemic": "good",
        "bmi_category": "normal",
        "complication_flags": {"hasEyeDisease": True}
    }
    
    sanitized, status, reason = validate_and_sanitize_prescription(mock_prescription, risk_result)
    
    assert status == "fallback"
    assert sanitized["activityPlan"][0]["intensity"] == "light"
    assert sanitized["activityPlan"][0]["duration"] == "10-15 minutes"
    
    # Test eye disease: removal of head-down exercises
    mock_prescription_yoga = {
        "planType": "plan_b_fitt",
        "activityPlan": [
            {"activityName": "Head Down Yoga Pose", "intensity": "light", "duration": "5 minutes", "frequency": "Daily", "progressionRule": "None", "safetyReason": "None", "ragSourceIds": [], "contraindicationChecksApplied": []}
        ],
        "simpleActivities": [],
        "strengthExercises": [],
        "personalizedTips": [],
        "safetyWarnings": []
    }
    
    sanitized_yoga, status_yoga, _ = validate_and_sanitize_prescription(mock_prescription_yoga, risk_result)
    assert status_yoga == "fallback"
    assert len(sanitized_yoga["activityPlan"]) == 0
    
    # Test foot wounds: weight-bearing to non-weight-bearing transition
    mock_prescription_foot = {
        "planType": "plan_b_fitt",
        "activityPlan": [
            {"activityName": "Outdoor Walking", "intensity": "moderate", "duration": "30 minutes", "frequency": "5 days", "progressionRule": "None", "safetyReason": "None", "ragSourceIds": [], "contraindicationChecksApplied": []}
        ],
        "simpleActivities": [],
        "strengthExercises": [],
        "personalizedTips": [],
        "safetyWarnings": []
    }
    risk_result_foot = {
        "par_q_clearance_required": False,
        "glycemic": "good",
        "bmi_category": "normal",
        "complication_flags": {"hasFootWoundOrUlcer": True}
    }
    sanitized_foot, status_foot, _ = validate_and_sanitize_prescription(mock_prescription_foot, risk_result_foot)
    assert status_foot == "fallback"
    assert "seated" in sanitized_foot["activityPlan"][0]["activityName"].lower()
