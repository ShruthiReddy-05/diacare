from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ExerciseSuggestion(BaseModel):
    activityName: str = Field(..., description="Name of the exercise/activity")
    intensity: str = Field(..., description="Intensity level of the exercise (light, moderate, high)")
    duration: str = Field(..., description="Duration of exercise, e.g., '10-15 minutes'")
    frequency: str = Field(..., description="Frequency of exercise, e.g., '5 days per week'")
    progressionRule: str = Field(..., description="Guideline for progression, e.g., 'Increase by 5 minutes next week if comfortable'")
    safetyReason: str = Field(..., description="Safety explanation or rationale for recommending this exercise")
    ragSourceIds: List[str] = Field(default=[], description="Source RAG rule IDs grounding this recommendation")
    contraindicationChecksApplied: List[str] = Field(default=[], description="List of safety checks applied for complications/risks")

class PersonalizedTip(BaseModel):
    tipId: str = Field(..., description="Unique ID for the tip")
    tipText: str = Field(..., description="The tip instruction in the preferred language")
    category: str = Field(..., description="Category, e.g., 'foot_care', 'hypoglycemia', 'diet'")
    rationale: str = Field(..., description="Rationale for why this tip applies to the user")

class AiExercisePrescription(BaseModel):
    planType: str = Field(..., description="Type of plan: 'plan_a_start_slowly', 'plan_b_fitt', 'medical_clearance_required', 'light_activity_only'")
    userSummary: str = Field(..., description="High-level feedback summary for the user")
    activityPlan: List[ExerciseSuggestion] = Field(default=[], description="Aerobic exercise activities plan")
    simpleActivities: List[ExerciseSuggestion] = Field(default=[], description="Simple low-barrier activities")
    strengthExercises: List[ExerciseSuggestion] = Field(default=[], description="Strength/resistance exercises")
    personalizedTips: List[PersonalizedTip] = Field(default=[], description="Personalized tips based on user complications/risks")
    safetyWarnings: List[str] = Field(default=[], description="Core safety warnings for diabetes/exercise")
    medicalClearanceRequired: bool = Field(default=False, description="Flag indicating if medical clearance is required before starting")
    ragSourceIds: List[str] = Field(default=[], description="All RAG rule IDs used in generating this prescription")

class PrescriptionResponse(BaseModel):
    id: str
    user_id: str
    session_id: str
    plan_type: str
    prescription_snapshot: Dict[str, Any] # AiExercisePrescription parsed or serialized
    created_at: datetime

    class Config:
        from_attributes = True

class AiPrescriptionRequestResponse(BaseModel):
    id: str
    user_id: str
    session_id: str
    model_provider: str
    model_name: str
    temperature: float
    normalized_health_profile_json: Dict[str, Any]
    retrieved_rag_rule_ids: List[str]
    created_at: datetime

    class Config:
        from_attributes = True

class AiPrescriptionOutputResponse(BaseModel):
    id: str
    request_id: str
    raw_model_output_json: Dict[str, Any]
    validated_output_json: Optional[Dict[str, Any]] = None
    validation_status: str
    rejection_reason: Optional[str] = None
    final_prescription_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
