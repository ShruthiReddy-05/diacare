from typing import Dict, Any, Tuple, List

def validate_and_sanitize_prescription(prescription_dict: Dict[str, Any], risk_result: Dict[str, Any]) -> Tuple[Dict[str, Any], str, str]:
    # Set status as "passed" by default, change to "fallback" if we apply corrections
    status = "passed"
    reasons = []
    
    plan_type = prescription_dict.get("planType", "plan_a_start_slowly")
    medical_clearance = bool(risk_result.get("par_q_clearance_required", False)) or plan_type == "medical_clearance_required"
    comp_flags = risk_result.get("complication_flags", {})
    glycemic = risk_result.get("glycemic", "unknown")
    
    # Extract flag states
    has_neuropathy = bool(comp_flags.get("hasNeuropathySymptoms", False))
    has_eye_disease = bool(comp_flags.get("hasEyeDisease", False))
    has_kidney_disease = bool(comp_flags.get("hasKidneyDisease", False))
    has_foot_wound = bool(comp_flags.get("hasFootWoundOrUlcer", False))
    has_fall_history = bool(comp_flags.get("hasFallHistory", False))
    
    # 1. Validate plan type matches medical clearance if required
    if medical_clearance and plan_type != "medical_clearance_required":
        prescription_dict["planType"] = "medical_clearance_required"
        prescription_dict["medicalClearanceRequired"] = True
        status = "fallback"
        reasons.append("Forced planType to medical_clearance_required due to PAR-Q/complication flags.")
        
    # We will sanitize the exercise groups: activityPlan, simpleActivities, strengthExercises
    groups = ["activityPlan", "simpleActivities", "strengthExercises"]
    
    for group_name in groups:
        exercises = prescription_dict.get(group_name, [])
        sanitized_exercises = []
        
        for ex in exercises:
            name = str(ex.get("activityName", "")).lower()
            intensity = str(ex.get("intensity", "")).lower()
            
            # Rule A: Reject vigorous or high-intensity exercises when contraindicated
            # Contraindicated if: eye disease, kidney disease, foot wounds, high sugar/red flag, or par_q clearance required
            contraindicate_vigorous = has_eye_disease or has_kidney_disease or has_foot_wound or glycemic == "red_flag" or medical_clearance
            if contraindicate_vigorous and intensity in ["high", "vigorous", "brisk"]:
                ex["intensity"] = "light"
                ex["duration"] = "10-15 minutes"
                ex["progressionRule"] = "Keep at current duration until cleared by doctor"
                status = "fallback"
                reasons.append(f"Reduced intensity of '{ex['activityName']}' to light because vigorous exercise is contraindicated.")
            
            # Rule B: Reject head-down exercises for eye disease
            if has_eye_disease and any(x in name for x in ["head down", "head-down", "downward dog", "inversion", "gymnastics"]):
                status = "fallback"
                reasons.append(f"Removed head-down exercise '{ex['activityName']}' for diabetic eye disease safety.")
                continue # Skip this exercise entirely
                
            # Rule C: Reject weight-bearing/prolonged walking for foot wounds
            if has_foot_wound and any(x in name for x in ["walk", "jog", "run", "hiking", "trekking", "standing"]):
                # Replace with seated equivalent or discard
                ex["activityName"] = "Seated arm swings and leg extensions"
                ex["intensity"] = "light"
                ex["duration"] = "10 minutes"
                ex["progressionRule"] = "Maintain seated exercise without weight bearing."
                status = "fallback"
                reasons.append(f"Modified weight-bearing exercise '{ex['activityName']}' to seated movements due to active foot wound.")
                
            # Rule D: Reject balance-challenging or barefoot exercises for neuropathy/fall risk
            if (has_neuropathy or has_fall_history) and any(x in name for x in ["barefoot", "one leg", "single leg", "unsupported", "balance beam"]):
                ex["activityName"] = "Supported toe stands (holding a chair)"
                ex["progressionRule"] = "Always hold a stable support. Do not perform unsupported balance exercises."
                status = "fallback"
                reasons.append(f"Replaced balance-challenging/barefoot exercise '{ex['activityName']}' with supported toe stands for neuropathy/fall risk safety.")
                
            sanitized_exercises.append(ex)
            
        prescription_dict[group_name] = sanitized_exercises
        
    # 2. Add required safety warnings in case of medical clearance or specific complications
    safety_warnings = prescription_dict.get("safetyWarnings", [])
    
    if medical_clearance and not any("medical clearance" in w.lower() for w in safety_warnings):
        safety_warnings.insert(0, "Please consult a healthcare professional before beginning any physical activity.")
        
    if (has_neuropathy or has_foot_wound) and not any("check feet" in w.lower() or "footwear" in w.lower() for w in safety_warnings):
        safety_warnings.append("Check your feet daily for cuts, redness, or blisters. Always wear protective, well-fitting footwear.")
        
    if (uses_insulin := bool(risk_result.get("glycemic") == "high" or comp_flags.get("hasExerciseHypoglycemiaHistory"))) and not any("glucose" in w.lower() or "sugar" in w.lower() for w in safety_warnings):
        safety_warnings.append("Carry a glucose source (like juice or sugar tablets) and monitor your blood sugar before and after activity.")
        
    prescription_dict["safetyWarnings"] = safety_warnings
    
    # 3. If medical clearance is required, enforce that all activities in the plan are safe and light
    if medical_clearance:
        # Limit activity plan to simple gentle walking or stretching
        if not prescription_dict.get("activityPlan"):
            prescription_dict["activityPlan"] = [{
                "activityName": "Comfortable leisurely walking",
                "intensity": "light",
                "duration": "10-15 minutes",
                "frequency": "3-5 days per week",
                "progressionRule": "Do not increase duration or intensity until medical clearance is obtained.",
                "safetyReason": "Light exercise is safe while awaiting medical consultation.",
                "ragSourceIds": ["RAG_010"],
                "contraindicationChecksApplied": ["par_q_clearance"]
            }]
            
    rejection_reason = "; ".join(reasons) if reasons else None
    return prescription_dict, status, rejection_reason
