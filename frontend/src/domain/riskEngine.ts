import type { RiskResult, AssessmentState, AiExercisePrescription } from './types';

export function calculateBmi(heightCm?: number, weightKg?: number): number {
  if (!heightCm || !weightKg || heightCm <= 0) return 0;
  return Math.round((weightKg / Math.pow(heightCm / 100, 2)) * 100) / 100;
}

export function classifyBmi(bmi: number): RiskResult['bmi_category'] {
  if (bmi <= 0) return "unknown";
  if (bmi < 18.5) return "underweight";
  if (bmi <= 22.9) return "normal";
  if (bmi <= 27.4) return "overweight";
  return "obese";
}

export function classifyGlycemic(hba1c?: number, fastingSugar?: number): RiskResult['glycemic'] {
  if (fastingSugar !== undefined && fastingSugar > 300) {
    return "red_flag";
  }
  if (hba1c !== undefined) {
    if (hba1c < 7) return "good";
    if (hba1c <= 9) return "moderate";
    return "high";
  }
  if (fastingSugar !== undefined) {
    if (fastingSugar < 130) return "good";
    if (fastingSugar <= 180) return "moderate";
    return "high";
  }
  return "good"; // fallback
}

export function calculateMETMinWeek(state: AssessmentState): number {
  const vigorousDays = state.vigorousDays ?? 0;
  const vigorousMinutes = state.vigorousMinutes ?? 0;
  const moderateDays = state.moderateDays ?? 0;
  const moderateMinutes = state.moderateMinutes ?? 0;
  const walkingDays = state.walkingDays ?? 0;
  const walkingMinutes = state.walkingMinutes ?? 0;

  const vigorousMET = vigorousDays * vigorousMinutes * 8.0;
  const moderateMET = moderateDays * moderateMinutes * 4.0;
  const walkingMET = walkingDays * walkingMinutes * 3.3;

  return Math.round(vigorousMET + moderateMET + walkingMET);
}

export function classifyPhysicalActivity(metMinPerWeek: number): RiskResult['physicalActivity'] {
  if (metMinPerWeek >= 3000) return "adequate";
  if (metMinPerWeek >= 600) return "moderate";
  return "low";
}

export function classifySedentary(sittingHours: number): RiskResult['sedentary'] {
  return sittingHours < 4 ? "low" : "moderate_to_high";
}

export function evaluateParQ(state: AssessmentState): boolean {
  const parqKeys: (keyof AssessmentState)[] = [
    "parqHeartCondition",
    "parqChestPainActivity",
    "parqChestPainRest",
    "parqDizziness",
    "parqBoneJoint",
    "parqDrugs",
    "parqOtherReason"
  ];
  return parqKeys.some(key => state[key] === true);
}

export function buildComplicationFlags(state: AssessmentState): RiskResult['complication_flags'] {
  return {
    hasHypertension: !!state.hasHypertension,
    hasNeuropathySymptoms: !!state.hasNeuropathySymptoms,
    hasEyeDisease: !!state.hasEyeDisease,
    hasKidneyDisease: !!state.hasKidneyDisease,
    hasFootWoundOrUlcer: !!state.hasFootWoundOrUlcer,
    hasExerciseHypoglycemiaHistory: !!state.hasExerciseHypoglycemiaHistory,
    hasFallHistory: !!state.hasFallHistory
  };
}

export function selectPlanType(riskResult: Partial<RiskResult>, state: AssessmentState): AiExercisePrescription['planType'] {
  const parQ = !!riskResult.par_q_clearance_required;
  const comp = riskResult.complication_flags || {
    hasHypertension: false,
    hasNeuropathySymptoms: false,
    hasEyeDisease: false,
    hasKidneyDisease: false,
    hasFootWoundOrUlcer: false,
    hasExerciseHypoglycemiaHistory: false,
    hasFallHistory: false
  };
  const glycemic = riskResult.glycemic || "good";
  const bmi_cat = riskResult.bmi_category || "normal";
  const pa = riskResult.physicalActivity || "low";
  
  const hba1c = state.hba1c;
  const hba1cHigh = hba1c !== undefined && hba1c >= 8.0;

  if (parQ || comp.hasKidneyDisease || glycemic === "red_flag" || hba1cHigh) {
    return "medical_clearance_required";
  }
  
  const hasComplications = 
    comp.hasNeuropathySymptoms ||
    comp.hasEyeDisease ||
    comp.hasFootWoundOrUlcer ||
    comp.hasExerciseHypoglycemiaHistory ||
    comp.hasFallHistory ||
    comp.hasHypertension;
    
  const lowConfidence = state.confidenceLevel !== undefined && state.confidenceLevel < 5;
  
  if (pa === "low" || bmi_cat === "obese" || hasComplications || lowConfidence) {
    return "plan_a_start_slowly";
  }
  
  return "plan_b_fitt";
}

export function calculateRisk(state: AssessmentState): RiskResult {
  const bmi = calculateBmi(state.heightCm, state.weightKg);
  const bmi_category = classifyBmi(bmi);
  const glycemic = classifyGlycemic(state.hba1c, state.fastingSugar);
  
  const metMinPerWeek = calculateMETMinWeek(state);
  const physicalActivity = classifyPhysicalActivity(metMinPerWeek);
  
  const sedentary = classifySedentary(state.sittingHours || 0);
  const par_q_clearance_required = evaluateParQ(state);
  const complication_flags = buildComplicationFlags(state);
  
  // Calculate overall risk
  let overall: RiskResult['overall'] = "low";
  const hasHighRisk = 
    par_q_clearance_required || 
    glycemic === "high" || 
    glycemic === "red_flag" || 
    physicalActivity === "low" || 
    Object.values(complication_flags).some(v => v);
    
  if (hasHighRisk) {
    overall = "high";
  } else if (glycemic === "moderate" || physicalActivity === "moderate" || sedentary === "moderate_to_high") {
    overall = "moderate";
  }
  
  return {
    glycemic,
    physicalActivity,
    sedentary,
    bmi_category,
    par_q_clearance_required,
    complication_flags,
    overall
  };
}
