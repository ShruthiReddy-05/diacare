export type LanguageCode = "en" | "ta";

export interface LocalizedText {
  en: string;
  ta: string;
}

export interface OptionDefinition {
  value: string;
  label: LocalizedText;
  nextQuestionId?: string; // Branching rule specific to this option
}

export interface BranchRule {
  dependsOn: string;
  equals?: any;
  notEquals?: any;
  nextQuestionId: string;
}

export interface ValidationRule {
  type: "required" | "min" | "max" | "regex";
  value?: any;
  message: LocalizedText;
}

export interface AudioAssetRef {
  assetId: string;
  url: string;
  provider: "sarvam" | "web_speech" | "manual";
  voiceId?: string;
  contentHash: string;
  durationMs?: number;
}

export type InputType =
  | "single_choice"
  | "multi_choice"
  | "number"
  | "decimal"
  | "text"
  | "date"
  | "scale"
  | "height_weight"
  | "duration"
  | "confirmation";

export interface QuestionDefinition {
  id: string;
  moduleId: string;
  prompt: LocalizedText;
  ttsPrompt?: LocalizedText;
  audio?: {
    en?: AudioAssetRef;
    ta?: AudioAssetRef;
  };
  inputType: InputType;
  options?: OptionDefinition[];
  min?: number;
  max?: number;
  unit?: string;
  required: boolean;
  saveAs: string;
  validation?: ValidationRule[];
  branching?: BranchRule[];
  aliases?: Record<string, string[]>;
  tags?: string[];
}

export interface QuestionnaireModule {
  id: string;
  title: LocalizedText;
  purpose: string;
  questions: QuestionDefinition[];
  outputLogicRefs?: string[];
}

export interface QuestionnaireDefinition {
  id: string;
  version: string;
  status: "draft" | "active" | "retired";
  title: LocalizedText;
  modules: QuestionnaireModule[];
}

export interface RiskResult {
  glycemic: "good" | "moderate" | "high" | "red_flag";
  physicalActivity: "adequate" | "moderate" | "low";
  sedentary: "low" | "moderate_to_high";
  bmi_category: "underweight" | "normal" | "overweight" | "obese" | "unknown";
  par_q_clearance_required: boolean;
  complication_flags: {
    hasHypertension: boolean;
    hasNeuropathySymptoms: boolean;
    hasEyeDisease: boolean;
    hasKidneyDisease: boolean;
    hasFootWoundOrUlcer: boolean;
    hasExerciseHypoglycemiaHistory: boolean;
    hasFallHistory: boolean;
  };
  overall: "low" | "moderate" | "high";
}

export interface ExerciseSuggestion {
  activityName: string;
  intensity: string;
  duration: string;
  frequency: string;
  progressionRule: string;
  safetyReason: string;
  ragSourceIds: string[];
  contraindicationChecksApplied: string[];
}

export interface PersonalizedTip {
  tipId: string;
  tipText: string;
  category: string;
  rationale: string;
}

export interface AiExercisePrescription {
  planType: "plan_a_start_slowly" | "plan_b_fitt" | "medical_clearance_required" | "light_activity_only";
  userSummary: string;
  activityPlan: ExerciseSuggestion[];
  simpleActivities: ExerciseSuggestion[];
  strengthExercises: ExerciseSuggestion[];
  personalizedTips: PersonalizedTip[];
  safetyWarnings: string[];
  medicalClearanceRequired: boolean;
  ragSourceIds: string[];
}

export interface UserProfile {
  id: string;
  display_user_id: string;
  first_name: string;
  last_name: string;
  preferred_language: LanguageCode;
  role: string;
}

export interface AssessmentState {
  language: LanguageCode;
  name?: string;
  age?: number;
  gender?: string;
  heightCm?: number;
  weightKg?: number;
  durationYears?: number;
  hba1c?: number;
  fastingSugar?: number;
  medications?: string;
  usesInsulin?: boolean;
  hasHypertension?: boolean;
  hasNeuropathySymptoms?: boolean;
  hasEyeDisease?: boolean;
  hasKidneyDisease?: boolean;
  hasFootWoundOrUlcer?: boolean;
  hasExerciseHypoglycemiaHistory?: boolean;
  hasFallHistory?: boolean;
  parqHeartCondition?: boolean;
  parqChestPainActivity?: boolean;
  parqChestPainRest?: boolean;
  parqDizziness?: boolean;
  parqBoneJoint?: boolean;
  parqDrugs?: boolean;
  parqOtherReason?: boolean;
  vigorousDays?: number;
  vigorousMinutes?: number;
  moderateDays?: number;
  moderateMinutes?: number;
  walkingDays?: number;
  walkingMinutes?: number;
  sittingHours?: number;
  confidenceLevel?: number;
  preferredExerciseTypes?: string[];
  enjoymentScore?: number;
  exerciseBarriers?: string[];
  sleepHours?: number;
  stressLevel?: string;
  junkFoodFrequency?: string;
  
  // App session identifiers
  user_id?: string;
  display_user_id?: string;
  first_name?: string;
  last_name?: string;
}
