"""Replaces services/rag_service.py: tag-intersection + precedence-sort
retrieval against the CareContentRule library, plus the held-back
'triggered content' release rule from the spec's design rule for My Care Plan."""
from typing import Any, Dict, List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.care_content_rule import CareContentRule


def build_content_tags(baseline: Dict[str, Any], module_outputs: Optional[Dict[str, Dict[str, Any]]] = None,
                        released_tags: Optional[List[str]] = None) -> List[str]:
    """Build an ordered, de-duplicated list of tags from a BaselineProfile-shaped
    dict and (optionally) module outcome outputs. Order is preserved (unlike the
    old rag_service.py, which lost ordering via set())."""
    tags: List[str] = []

    def add(tag: str):
        if tag not in tags:
            tags.append(tag)

    bmi_cat = baseline.get("bmi_category")
    if bmi_cat == "overweight":
        add("overweight")
    elif bmi_cat == "obese":
        add("obese")
        add("overweight")

    if baseline.get("waist_risk"):
        add("waist_risk")
    if baseline.get("sedentary_work_flag"):
        add("sedentary_work")
    if baseline.get("duration_risk_flag"):
        add("duration_gt_5")
    if baseline.get("bp_category") == "high":
        add("bp_high")
    if baseline.get("regimen_class") == "insulin":
        add("uses_insulin")
    elif baseline.get("regimen_class") == "sulfonylurea":
        add("uses_sulfonylurea")
    if baseline.get("hypoglycemia_risk_flag"):
        add("hypoglycemia_risk")
    if baseline.get("herbal_use_flag"):
        add("herbal_use")
    if baseline.get("follow_up_gap_flag"):
        add("follow_up_gap")

    screening = baseline.get("screening_overdue") or {}
    if screening.get("eye"):
        add("eye_screening_overdue")
    if screening.get("foot"):
        add("foot_screening_overdue")
    if screening.get("renal"):
        add("renal_screening_overdue")

    complications = baseline.get("complication_profile") or {}
    if complications.get("neuropathy"):
        add("neuropathy")
    if complications.get("retinopathy"):
        add("retinopathy")
    if complications.get("nephropathy"):
        add("nephropathy")
    if complications.get("cad"):
        add("cad")

    foot_risk = baseline.get("foot_risk_category")
    if foot_risk and foot_risk != "low":
        add(f"foot_risk_{foot_risk}")
    if baseline.get("exercise_clearance_required"):
        add("exercise_clearance_required")
    if baseline.get("tobacco_flag"):
        add("tobacco")
    if baseline.get("alcohol_flag"):
        add("alcohol")

    risk_tier = baseline.get("overall_risk_tier")
    if risk_tier:
        add(f"risk_{risk_tier}")

    for tag in (released_tags or []):
        add(tag)

    return tags


async def retrieve_applicable_content(session: AsyncSession, tags: List[str],
                                       module_id: Optional[str] = None) -> List[CareContentRule]:
    stmt = select(CareContentRule).where(CareContentRule.review_status == "approved")
    result = await session.execute(stmt)
    all_rules = result.scalars().all()

    applicable = []
    for rule in all_rules:
        if module_id and rule.module_id != module_id:
            continue
        # Held-back content only becomes eligible once its release_tag is in tags
        if rule.release_tag and rule.release_tag not in tags:
            continue
        if any(tag in tags for tag in rule.condition_tags):
            applicable.append(rule)

    applicable.sort(key=lambda r: r.precedence)
    return applicable
