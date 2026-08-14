export type LanguageCode = "en" | "ta";

export interface LocalizedText {
  en: string;
  ta: string;
}

export interface OptionDefinition {
  value: string;
  label: LocalizedText;
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
  | "blood_pressure"
  | "blood_sugar_target"
  | "confirmation";

export interface QuestionDefinition {
  id: string;
  moduleId: string;
  prompt: LocalizedText;
  inputType: InputType;
  options?: OptionDefinition[];
  min?: number;
  max?: number;
  unit?: string;
  required: boolean;
  saveAs: string;
}

export interface ConversationModule {
  id: string;
  title: LocalizedText;
  sitting: string; // "1", "2", "3", or "weekly"
  questions: QuestionDefinition[];
}

export interface ConversationScript {
  id: string;
  version: string;
  status: "draft" | "active" | "retired";
  title: LocalizedText;
  modules: ConversationModule[];
}

export interface UserProfile {
  id: string;
  display_user_id: string;
  first_name: string;
  last_name: string;
  preferred_language: LanguageCode;
  role: string;
}

// ── Derived, server-authoritative domain state ──
// Risk/plan classification is computed entirely by the backend decision
// engine (services/b1_engine.py .. checkin_engine.py); the frontend never
// recomputes it.

export interface BaselineProfile {
  id: string;
  user_id: string;
  age_band?: string | null;
  bmi?: number | null;
  bmi_category?: string | null;
  waist_risk: boolean;
  ideal_body_weight_kg?: number | null;
  daily_energy_kcal?: number | null;
  occupational_activity_level?: string | null;
  sedentary_work_flag: boolean;
  glycemic_category?: string | null;
  duration_risk_flag: boolean;
  bp_category?: string | null;
  salt_target_g?: number | null;
  regimen_class?: string | null;
  hypoglycemia_risk_flag: boolean;
  herbal_use_flag: boolean;
  follow_up_gap_flag: boolean;
  screening_overdue?: { eye: boolean; foot: boolean; renal: boolean } | null;
  complication_profile?: { neuropathy: boolean; retinopathy: boolean; nephropathy: boolean; cad: boolean } | null;
  foot_risk_category?: string | null;
  exercise_clearance_required: boolean;
  tobacco_flag: boolean;
  alcohol_flag: boolean;
  overall_risk_tier?: "red" | "amber" | "green" | null;
  computed_at: string;
}

export interface ModuleOutcome {
  id: string;
  user_id: string;
  module_id: string;
  output_json: Record<string, any>;
  computed_at: string;
}

// Mirrors services/care_plan_generator.py's plan_snapshot shape exactly
// (snake_case, since it's raw JSON straight from the backend).
export interface CarePlanSnapshot {
  disclaimer: string;
  clinical_status: {
    rows: { what: string; last_value: any; target: string; trace: string[] }[];
    note: string;
  };
  dietary_goals: {
    intro: string;
    goals: { text_en: string; trace: string[] }[];
    has_more_stored: boolean;
  };
  activity_plan: {
    activity_category: string | null;
    weekly_target: string | null;
    ramp_protocol: { weeks: string; daily_minutes: string; note: string }[] | null;
    activity_guidance?: string | null;
    post_meal_walk_emphasis: boolean | null;
    resistance_exercise?: { activity_name: string; duration: string; frequency: string } | null;
    movement_break_rule?: string;
    foot_precautions?: string[];
    glucose_check_note?: string;
    medical_clearance_note?: string;
    medical_clearance_required?: boolean;
  };
  sleep_and_stress: {
    sleep_apnea_risk_flag: boolean | null;
    coping_strategy: string | null;
  };
  medicines: {
    medications: any[];
    reminder_schedule: { label: string; time_of_day: string }[];
    adherence_boilerplate: string;
    herbal_note: string | null;
  };
  monitoring_plan: {
    monitoring_plan: Record<string, string> | null;
    target_card: { targets: Record<string, string>; note: string } | null;
    screening_overdue: { eye: boolean; foot: boolean; renal: boolean };
    next_visit_script: string | null;
  };
  conditional_hypo_protocol: {
    title: string;
    protocol_text_en: string;
    escalation_note: string;
  } | null;
  escalation: {
    title: string;
    bullets: string[];
  };
}

export interface CarePlan {
  id: string;
  user_id: string;
  session_id?: string | null;
  risk_tier?: string | null;
  plan_snapshot: CarePlanSnapshot;
  traceability: Record<string, string[]>;
  created_at: string;
}

export interface CheckInSession {
  id: string;
  user_id: string;
  schedule_id?: string | null;
  program_week: number;
  due_date: string;
  status: "due" | "missed" | "completed" | "escalated";
  q1_activity_days?: number | null;
  q2_food_goal_days?: number | null;
  q3_medication_days?: number | null;
  q4_foot_care_days?: number | null;
  q5_new_foot_problem?: boolean | null;
  q6_stress_0_10?: number | null;
  q7_sleep_0_10?: number | null;
  q8_sugar_reading?: number | null;
  q8b_hypo_episode?: boolean | null;
  triggered_content?: { sick_day: boolean; festival_fasting: boolean } | null;
  safety_flag: boolean;
  escalation_advice_given: boolean;
  completed_at?: string | null;
  created_at: string;
}
