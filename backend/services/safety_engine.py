"""Module D -- continuous safety monitoring, runs across every other module.
The rule engine, not the language model, decides every escalation.
Reference: ICMR 2018 Sec 8.1, 8.3, 8.5, 8.7.3."""
from typing import Any, Dict, List, Optional
from utils import safe_float

# trigger_code -> (answers key, human label)
BOOLEAN_RED_FLAGS = {
    "chest_pain": "chestPain",
    "breathlessness_at_rest": "breathlessnessAtRest",
    "severe_giddiness": "severeGiddiness",
    "fainting": "fainting",
    "confusion": "confusion",
    "repeated_vomiting": "repeatedVomiting",
    "cannot_keep_fluids": "cannotKeepFluidsDown",
    "foot_blackening": "footBlackening",
    "spreading_redness": "footSpreadingRedness",
    "foul_smell": "footFoulSmell",
    "sudden_vision_loss": "suddenVisionLoss",
    "reduced_urine_output": "reducedUrineOutput",
    "self_harm": "expressedSelfHarm",
}

TEXT_KEYWORD_MAP = {
    "chest_pain": ["chest pain", "chest tightness"],
    "breathlessness_at_rest": ["breathless", "can't breathe", "cannot breathe", "short of breath"],
    "severe_giddiness": ["giddiness", "giddy", "dizzy", "dizziness"],
    "fainting": ["faint", "fainted", "passed out", "unconscious"],
    "confusion": ["confused", "confusion", "disoriented"],
    "repeated_vomiting": ["vomiting", "vomit", "throwing up"],
    "cannot_keep_fluids": ["can't keep water", "cannot keep fluids", "keep nothing down"],
    "foot_blackening": ["black", "blackening", "gangrene"],
    "spreading_redness": ["spreading redness", "spreading red"],
    "foul_smell": ["foul smell", "bad smell", "pus"],
    "sudden_vision_loss": ["vision loss", "can't see", "cannot see", "blurred vision suddenly"],
    "reduced_urine_output": ["less urine", "reduced urine", "not passing urine"],
    "self_harm": [
        "kill myself", "end my life", "end it all", "not worth living", "want to die",
        "harm myself", "hurt myself", "suicide", "no reason to live",
    ],
}


def check_safety_values(answers: Dict[str, Any]) -> List[str]:
    """Inspect a normalized answers dict for boolean red-flag fields and
    out-of-range glucose readings. Returns a list of trigger codes."""
    triggered = []

    for code, key in BOOLEAN_RED_FLAGS.items():
        if bool(answers.get(key, False)):
            triggered.append(code)

    sugar = answers.get("sugarReading")
    if sugar is not None:
        s = safe_float(sugar)
        if s and s < 70:
            triggered.append("sugar_below_70")
        elif s and s > 400:
            triggered.append("sugar_above_400")

    return triggered


def scan_text_for_red_flags(text: Optional[str]) -> List[str]:
    """Best-effort keyword scan over free-text / voice-transcribed answers."""
    if not text:
        return []
    lowered = text.lower()
    triggered = []
    for code, keywords in TEXT_KEYWORD_MAP.items():
        if any(kw in lowered for kw in keywords):
            triggered.append(code)
    return triggered


EMERGENCY_SCRIPT = {
    "en": (
        "This needs urgent attention. Please stop and go to the nearest health facility now. "
        "I will not give any more self-care advice until you have been seen."
    ),
    "ta": (
        "இது உடனடி கவனிப்பு தேவைப்படுகிறது. தயவுசெய்து நிறுத்திவிட்டு இப்போதே அருகிலுள்ள மருத்துவமனைக்குச் செல்லுங்கள். "
        "நீங்கள் பரிசோதிக்கப்படும் வரை நான் மேலும் சுய-பராமரிப்பு ஆலோசனை வழங்க மாட்டேன்."
    ),
}


def check_safety(answers: Dict[str, Any], free_text: Optional[str] = None) -> List[str]:
    """Single entry point: combine structured-field and free-text checks,
    deduplicated, order-preserving."""
    triggered = check_safety_values(answers)
    for code in scan_text_for_red_flags(free_text):
        if code not in triggered:
            triggered.append(code)
    return triggered
