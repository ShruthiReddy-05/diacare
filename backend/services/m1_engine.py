"""Module M1 -- Healthy Eating (AADE7: Healthy Eating).
Reference: ICMR 2018 Sec 6.2, 6.2.1, 6.2.2.
Only the two largest gaps become active goals; the rest are stored and
released in later fortnights (see the spec's design rule for My Care Plan)."""
from typing import Any, Dict, List
from utils import safe_float, safe_int

FRIED_SWEET_THRESHOLD_PER_WEEK = 3
VEGETABLE_PORTION_TARGET = 3
MEAL_FREQUENCY_TARGET = 4


def classify_meal_pattern(meals_per_day: Any, meal_skipping: bool) -> str:
    meals = safe_int(meals_per_day)
    if meal_skipping or meals < MEAL_FREQUENCY_TARGET:
        return "few_large_meals"
    return "adequate_frequency"


def is_hypo_risk_routed(meal_skipping: bool, hypoglycemia_risk_flag: bool) -> bool:
    """Meal skipping while on sulfonylurea/insulin is a hypoglycaemia risk,
    not just a diet issue -- route to M4."""
    return bool(meal_skipping and hypoglycemia_risk_flag)


def classify_carb_load(rice_cups_per_meal: Any) -> str:
    cups = safe_float(rice_cups_per_meal)
    if cups <= 1:
        return "low"
    if cups <= 2:
        return "moderate"
    return "high"


def classify_salt(bp_category: str, adds_extra_salt: bool, eats_pickles_often: bool) -> Dict[str, Any]:
    flagged = bool(adds_extra_salt or eats_pickles_often)
    target_g = 3.0 if bp_category == "high" else 5.0
    return {"flagged": flagged, "salt_target_g": target_g}


def build_candidate_goals(answers: Dict[str, Any], bp_category: str, nephropathy: bool = False) -> List[Dict[str, Any]]:
    candidates = []

    rice_cups = safe_float(answers.get("riceCupsPerMeal"))
    eats_millets = bool(answers.get("eatsMilletsWholeWheat", False))
    if rice_cups >= 1 and not eats_millets:
        candidates.append({
            "goal_id": "reduce_rice_add_millets",
            "text_en": "Replace one cup of white rice at a meal with millet or whole wheat, five days a week.",
            "gap_score": rice_cups,
        })

    fried_sweet_freq = safe_float(answers.get("friedSweetFrequencyPerWeek"))
    if fried_sweet_freq >= FRIED_SWEET_THRESHOLD_PER_WEEK:
        candidates.append({
            "goal_id": "reduce_fried_sweet",
            "text_en": "Cut fried snacks, sweets, or bakery items to less than 3 times a week.",
            "gap_score": fried_sweet_freq,
        })

    veg_portions = safe_float(answers.get("vegetablePortionsPerDay"))
    if veg_portions < VEGETABLE_PORTION_TARGET:
        candidates.append({
            "goal_id": "add_vegetable_portion",
            "text_en": "Add one extra portion of vegetables or greens daily.",
            "gap_score": VEGETABLE_PORTION_TARGET - veg_portions,
        })

    # Nephropathy: no sodium target is issued here; salt advice defers to the doctor.
    salt = classify_salt(bp_category, answers.get("addsExtraSalt", False), answers.get("eatsPicklesOrPackagedSnacksOften", False))
    if salt["flagged"] and not nephropathy:
        candidates.append({
            "goal_id": "reduce_salt",
            "text_en": f"Stop adding extra salt at the table; keep total salt under {salt['salt_target_g']:g} g a day.",
            "gap_score": 2.0 if bp_category == "high" else 1.0,
        })

    meals_per_day = safe_int(answers.get("mealsPerDay"))
    if meals_per_day and meals_per_day < MEAL_FREQUENCY_TARGET:
        candidates.append({
            "goal_id": "split_meals",
            "text_en": "Split large meals into 5-6 smaller meals across the day.",
            "gap_score": float(MEAL_FREQUENCY_TARGET - meals_per_day),
        })

    candidates.sort(key=lambda g: g["gap_score"], reverse=True)
    return candidates


def compute_m1(answers: Dict[str, Any], bp_category: str = "target",
               hypoglycemia_risk_flag: bool = False, nephropathy: bool = False,
               max_active_goals: int = 2) -> Dict[str, Any]:
    meal_skipping = bool(answers.get("skipsMeals", False))
    candidates = build_candidate_goals(answers, bp_category, nephropathy)
    active_goals = candidates[:max_active_goals]
    stored_goals = candidates[max_active_goals:]

    return {
        "meal_pattern": classify_meal_pattern(answers.get("mealsPerDay"), meal_skipping),
        "hypo_risk_routed_to_m4": is_hypo_risk_routed(meal_skipping, hypoglycemia_risk_flag),
        "carb_load_category": classify_carb_load(answers.get("riceCupsPerMeal")),
        "fibre_gap": safe_float(answers.get("vegetablePortionsPerDay")) < VEGETABLE_PORTION_TARGET,
        "salt": classify_salt(bp_category, answers.get("addsExtraSalt", False), answers.get("eatsPicklesOrPackagedSnacksOften", False)),
        "candidate_goals": candidates,
        "active_goals": active_goals,
        "stored_goals": stored_goals,
    }
