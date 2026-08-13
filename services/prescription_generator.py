import json
import logging
import httpx
from typing import Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from services.rag_service import build_health_tags, retrieve_applicable_rules
from services.risk_engine import select_plan_type
from services.prescription_validator import validate_and_sanitize_prescription
from schemas.prescription import AiExercisePrescription

logger = logging.getLogger(__name__)

# Fallback generator in case of network errors or missing API keys
def generate_rule_based_fallback(health_tags: List[str], risk_result: Dict[str, Any], answers: Dict[str, Any], plan_type: str) -> Dict[str, Any]:
    logger.info("Generating rule-based fallback prescription")
    
    # 1. Determine medical clearance
    med_clearance = plan_type == "medical_clearance_required"
    
    # 2. Build personalized tips from health tags
    personalized_tips = []
    safety_warnings = []
    rag_ids = []
    
    # Map tag to tip
    tag_tips = {
        "overweight": ("TIP_001", "Since you are overweight, choose low-impact exercises like walking or stationary cycling to protect your joints.", "weight_management", "BMI indicates overweight/obesity"),
        "obese": ("TIP_002", "Reduce weight gradually. Choose low-impact activities and avoid sudden heavy weight bearing.", "weight_management", "BMI indicates obesity"),
        "duration_gt_5": ("TIP_003", "Since you have had diabetes for over 5 years, pay close attention to any unusual fatigue or glucose changes.", "fatigue_monitoring", "Diabetes duration > 5 years"),
        "uses_insulin": ("TIP_004", "Always carry a snack or glucose source (like juice or tablets). Do not exercise on an empty stomach.", "hypoglycemia", "Insulin user"),
        "neuropathy": ("TIP_005", "Check your feet daily for cuts, redness, or blisters. Avoid barefoot exercise and walking on uneven ground.", "foot_care", "Peripheral neuropathy symptoms present"),
        "eye_disease": ("TIP_006", "Avoid head-down positions (like certain yoga poses) and head-impact activities to protect your eyes.", "retinopathy", "Diabetic eye disease history"),
        "foot_wounds": ("TIP_007", "Use chair-based or seated exercises. Non-weight-bearing exercises are preferred until your foot wound heals.", "foot_care", "Active foot wound/ulcer present"),
        "hypoglycemia_history": ("TIP_008", "Monitor blood sugar before and after physical activity. Keep glucose tablets or juice nearby.", "hypoglycemia", "Prior exercise-induced hypoglycemia"),
        "sedentary_gt_4": ("TIP_009", "Stand up and move for 3 minutes every 30-60 minutes. Avoid sitting continuously.", "sedentary", "Sitting time is 4+ hours per day"),
        "low_confidence": ("TIP_010", "Focus on small, achievable daily walks (e.g. 5-10 mins) to build consistency and confidence.", "motivation", "Low exercise confidence"),
        "barrier_time": ("TIP_011", "Try breaking your activity into three short 10-minute walks spread throughout the day.", "motivation", "Lack of time barrier reported"),
        "barrier_pain_fatigue": ("TIP_012", "When feeling tired or in pain, modify your workout to lighter seated stretches or a slow walk.", "motivation", "Pain/fatigue barriers reported"),
        "poor_sleep_stress": ("TIP_013", "Lower exercise intensity on high-stress or poor-sleep days. Try gentle stretching or breathing exercises.", "sleep_stress", "Poor sleep / high stress"),
        "junk_food": ("TIP_014", "Support your exercise energy by drinking plenty of water and choosing fiber-rich foods.", "diet", "Frequent junk food consumption")
    }
    
    for tag in health_tags:
        if tag in tag_tips:
            tip_id, text, cat, rational = tag_tips[tag]
            personalized_tips.append({
                "tipId": tip_id,
                "tipText": text,
                "category": cat,
                "rationale": rational
            })
            rag_ids.append(f"RAG_{tip_id.split('_')[1]}")
            
    # Add safety warnings
    if med_clearance:
        safety_warnings.append("Please consult a healthcare professional before beginning any physical activity.")
        rag_ids.append("RAG_010")
    if "neuropathy" in health_tags or "foot_wounds" in health_tags:
        safety_warnings.append("Check your feet daily for cuts, redness, or blisters. Always wear protective, dry footwear.")
        rag_ids.append("RAG_004")
    if "uses_insulin" in health_tags or "hypoglycemia_history" in health_tags:
        safety_warnings.append("Carry a glucose source and monitor your blood sugar before and after activity.")
        rag_ids.append("RAG_003")
        
    # Standard Aerobic Plan
    activity_plan = []
    simple_activities = []
    
    if med_clearance:
        activity_plan.append({
            "activityName": "Comfortable leisurely walking",
            "intensity": "light",
            "duration": "10-15 minutes",
            "frequency": "3-5 days per week",
            "progressionRule": "Do not increase duration or intensity until medical clearance is obtained.",
            "safetyReason": "Light physical activity is safe while awaiting doctor review.",
            "ragSourceIds": ["RAG_010"],
            "contraindicationChecksApplied": ["par_q_clearance"]
        })
        simple_activities.append({
            "activityName": "Gentle stretching and breathing exercises",
            "intensity": "light",
            "duration": "5-10 minutes",
            "frequency": "Daily",
            "progressionRule": "Keep intensity light.",
            "safetyReason": "Safe, non-stressful mobility exercises.",
            "ragSourceIds": ["RAG_010"],
            "contraindicationChecksApplied": []
        })
    elif plan_type == "plan_a_start_slowly":
        activity_plan.append({
            "activityName": "Comfortable leisurely walking",
            "intensity": "light",
            "duration": "10-15 minutes",
            "frequency": "5 days per week",
            "progressionRule": "Increase duration by 5 minutes each week as comfortable, targeting 30 minutes.",
            "safetyReason": "Beginner pace is safe and builds baseline cardiovascular capacity.",
            "ragSourceIds": ["RAG_016"],
            "contraindicationChecksApplied": []
        })
        simple_activities.append({
            "activityName": "Walking around the home or garden",
            "intensity": "light",
            "duration": "10 minutes",
            "frequency": "After lunch and dinner",
            "progressionRule": "Consistent short walks after meals.",
            "safetyReason": "Promotes postprandial glucose uptake.",
            "ragSourceIds": ["RAG_016"],
            "contraindicationChecksApplied": []
        })
    else: # plan_b_fitt
        activity_plan.append({
            "activityName": "Brisk walking",
            "intensity": "moderate",
            "duration": "30 minutes",
            "frequency": "5 days per week",
            "progressionRule": "Try incorporating light intervals of faster walking or gentle cycling as fitness improves.",
            "safetyReason": "Brisk walking is safe and highly effective for HbA1c reduction when no complications exist.",
            "ragSourceIds": ["RAG_017"],
            "contraindicationChecksApplied": []
        })
        simple_activities.append({
            "activityName": "Active chores or yard work",
            "intensity": "light",
            "duration": "15-20 minutes",
            "frequency": "Daily",
            "progressionRule": "Maintain daily activity levels.",
            "safetyReason": "Increases daily non-exercise activity thermogenesis (NEAT).",
            "ragSourceIds": ["RAG_017"],
            "contraindicationChecksApplied": []
        })
        
    # Strength exercises
    strength_exercises = []
    # If not severely contraindicated (like kidney disease or active foot wound, which we handle during validation)
    if not med_clearance and "foot_wounds" not in health_tags:
        strength_exercises.append({
            "activityName": "Chair sit-to-stands and wall push-ups",
            "intensity": "moderate",
            "duration": "1-2 sets of 10-15 repetitions",
            "frequency": "2-3 non-consecutive days per week",
            "progressionRule": "Increase repetitions up to 15, then increase sets to 3.",
            "safetyReason": "Increases muscular glucose uptake safely using bodyweight.",
            "ragSourceIds": ["RAG_018"],
            "contraindicationChecksApplied": []
        })
        rag_ids.append("RAG_018")
    elif "foot_wounds" in health_tags:
        # Seated strength only
        strength_exercises.append({
            "activityName": "Seated leg extensions and supported wall pushups",
            "intensity": "light",
            "duration": "1 set of 10 repetitions",
            "frequency": "2 days per week",
            "progressionRule": "Keep load light and completely non-weight-bearing.",
            "safetyReason": "Avoids pressure on the active foot ulcer while maintaining strength.",
            "ragSourceIds": ["RAG_007", "RAG_018"],
            "contraindicationChecksApplied": ["foot_wound_check"]
        })
        rag_ids.append("RAG_007")
        rag_ids.append("RAG_018")
        
    user_summary = "Based on your health assessment, I have prepared a safe and gradual plan to help manage your diabetes through light-to-moderate physical activity."
    if med_clearance:
        user_summary = "Based on your risk screening, please obtain medical clearance from your doctor before starting moderate-to-vigorous exercise. I have provided a light plan you can safely discuss with them."
        
    return {
        "planType": plan_type,
        "userSummary": user_summary,
        "activityPlan": activity_plan,
        "simpleActivities": simple_activities,
        "strengthExercises": strength_exercises,
        "personalizedTips": personalized_tips,
        "safetyWarnings": safety_warnings,
        "medicalClearanceRequired": med_clearance,
        "ragSourceIds": list(set(rag_ids))
    }

async def generate_prescription(session: AsyncSession, user_id: str, session_id: str, risk_result: Dict[str, Any], answers: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Determine plan type
    plan_type = select_plan_type(risk_result, answers)
    
    # 2. Build health tags
    health_tags = build_health_tags(risk_result, answers, plan_type)
    
    # 3. Retrieve applicable RAG rules
    rules = await retrieve_applicable_rules(session, health_tags)
    rag_source_ids = [rule.id for rule in rules]
    
    prescription_data = None
    
    # 4. Attempt Together AI call if API key is present
    if settings.TOGETHER_API_KEY:
        try:
            logger.info("Attempting AI exercise prescription generation via Together AI")
            
            # Format rules text
            rules_formatted = []
            for rule in rules:
                rules_formatted.append(
                    f"Rule ID: {rule.id}\n"
                    f"Condition: {', '.join(rule.condition_tags)}\n"
                    f"Severity: {rule.severity}\n"
                    f"Recommendation: {rule.recommendation}\n"
                    f"Rationale: {rule.rationale}\n"
                )
            rules_text = "\n---\n".join(rules_formatted)
            
            # Setup prompt and context
            user_profile_summary = {
                "age": answers.get("age"),
                "gender": answers.get("gender"),
                "bmi": risk_result.get("bmi_category"),
                "glycemic_control": risk_result.get("glycemic"),
                "complications": risk_result.get("complication_flags"),
                "insulin_use": str(answers.get("medications")).lower() in ["insulin", "both"],
                "physical_activity_level": risk_result.get("physical_activity"),
                "sedentary_hours": answers.get("sittingHours"),
                "confidence_level": answers.get("confidenceLevel"),
                "enjoyment_score": answers.get("enjoymentScore"),
                "barriers": answers.get("exerciseBarriers"),
                "preferred_exercises": answers.get("preferredExerciseTypes"),
                "sleep_hours": answers.get("sleepHours"),
                "stress_level": answers.get("stressLevel"),
                "junk_food_frequency": answers.get("junkFoodFrequency")
            }
            
            system_instruction = (
                "You are DiaFit, a clinical AI diabetes exercise coach. Your task is to generate a personalized, safe physical activity prescription in JSON format.\n"
                "You MUST follow the clinical safety and RAG rules provided. Under no circumstances should user preferences override safety warnings.\n\n"
                "Your output JSON MUST strictly match the following structure:\n"
                "{\n"
                "  \"planType\": \"plan_a_start_slowly\" | \"plan_b_fitt\" | \"medical_clearance_required\" | \"light_activity_only\",\n"
                "  \"userSummary\": \"A short motivational, bilingual or simple summary text in English (or preferred language if asked).\",\n"
                "  \"activityPlan\": [\n"
                "     { \"activityName\": \"string\", \"intensity\": \"light\"|\"moderate\", \"duration\": \"string\", \"frequency\": \"string\", \"progressionRule\": \"string\", \"safetyReason\": \"string\", \"ragSourceIds\": [\"string\"], \"contraindicationChecksApplied\": [\"string\"] }\n"
                "  ],\n"
                "  \"simpleActivities\": [ ... same structure as activityPlan ... ],\n"
                "  \"strengthExercises\": [ ... same structure as activityPlan ... ],\n"
                "  \"personalizedTips\": [\n"
                "     { \"tipId\": \"string\", \"tipText\": \"string\", \"category\": \"string\", \"rationale\": \"string\" }\n"
                "  ],\n"
                "  \"safetyWarnings\": [ \"string\" ],\n"
                "  \"medicalClearanceRequired\": boolean,\n"
                "  \"ragSourceIds\": [ \"string\" ]\n"
                "}\n"
            )
            
            user_prompt = (
                f"### User Health Profile\n{json.dumps(user_profile_summary, indent=2)}\n\n"
                f"### Clinically Approved RAG Rules\nUse these rules to construct the prescription. Only suggest exercises that comply with the allowed/prohibited constraints of these rules.\n\n{rules_text}\n\n"
                f"### Prescribed Plan Type\n{plan_type}\n\n"
                "Generate the exercise prescription in strict JSON format now."
            )
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.together.xyz/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.TOGETHER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.get_llm_model(),
                        "messages": [
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": settings.LLM_TEMPERATURE,
                        "max_tokens": settings.LLM_MAX_TOKENS,
                        "response_format": {"type": "json_object"}
                    }
                )
                
                if response.status_code == 200:
                    response_json = response.json()
                    content = response_json["choices"][0]["message"]["content"]
                    prescription_data = json.loads(content)
                    logger.info("Successfully received exercise prescription from Together AI")
                else:
                    logger.warning(f"Together AI API returned error status: {response.status_code}. Response: {response.text}")
                    
        except Exception as e:
            logger.error(f"Failed to generate prescription via Together AI: {e}", exc_info=True)
            
    # 5. Apply rule-based fallback if AI generation failed or wasn't attempted
    if not prescription_data:
        prescription_data = generate_rule_based_fallback(health_tags, risk_result, answers, plan_type)
        
    # 6. Safety validation and sanitization
    sanitized_prescription, validation_status, rejection_reason = validate_and_sanitize_prescription(
        prescription_data, risk_result
    )
    
    # Store validation results inside a return dict
    return {
        "plan_type": sanitized_prescription.get("planType", plan_type),
        "prescription_snapshot": sanitized_prescription,
        "validation_status": validation_status,
        "rejection_reason": rejection_reason,
        "rag_source_ids": list(set(sanitized_prescription.get("ragSourceIds", rag_source_ids)))
    }
