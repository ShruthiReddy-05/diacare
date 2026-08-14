"""Seeds the CareContentRule library. Run via:
    python -m data.seed_care_content
(run from backend/, matching the old seed_rag_rules.py convention).
Each row's source_reference is the ICMR section / AADE7 domain it comes
from, so this seed data doubles as the spec's traceability table."""
import asyncio
from sqlalchemy.future import select
from database import AsyncSessionLocal, Base, engine
from models.care_content_rule import CareContentRule

RULES = [
    {
        "id": "CONTENT_001", "module_id": "B1", "content_type": "tip",
        "condition_tags": ["overweight", "obese"],
        "text_en": "Gradual weight reduction toward a BMI of 20-23; reduce daily energy by no more than 500 kcal/day; prefer low-impact activity.",
        "text_ta": "படிப்படியாக எடையை 20-23 BMI நோக்கி குறைக்கவும்; தினசரி உணவு ஆற்றலை 500 கிலோகலோரிக்கு மேல் குறைக்க வேண்டாம்; குறைந்த அழுத்த உடற்பயிற்சிகளை விரும்பவும்.",
        "severity": "info", "precedence": 10, "source_reference": "ICMR 2018 Sec 4.1",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_002", "module_id": "B1", "content_type": "tip",
        "condition_tags": ["waist_risk"],
        "text_en": "Your BMI may be normal, but your waist size adds risk. Prioritise carbohydrate quality and activity rather than calorie restriction.",
        "text_ta": "உங்கள் BMI சாதாரணமாக இருந்தாலும், இடுப்பு அளவு ஆபத்தை அதிகரிக்கிறது. கலோரி கட்டுப்பாட்டை விட, மாவுச்சத்து தரம் மற்றும் உடற்செயல்பாட்டிற்கு முன்னுரிமை கொடுங்கள்.",
        "severity": "info", "precedence": 10, "source_reference": "ICMR 2018 Sec 6.2.1",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_003", "module_id": "B1", "content_type": "tip",
        "condition_tags": ["sedentary_work"],
        "text_en": "Stand and move for 3 minutes every 30-60 minutes.",
        "text_ta": "ஒவ்வொரு 30-60 நிமிடங்களுக்கும், 3 நிமிடங்கள் எழுந்து நடமாடுங்கள்.",
        "severity": "info", "precedence": 10, "source_reference": "ICMR 2018 Sec 10.3",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_004", "module_id": "B2", "content_type": "warning",
        "condition_tags": ["bp_high"],
        "text_en": "Your blood pressure needs a recheck and doctor review. Keep total salt under 3 g a day.",
        "text_ta": "உங்கள் இரத்த அழுத்தத்தை மீண்டும் பரிசோதித்து மருத்துவரிடம் காட்ட வேண்டும். மொத்த உப்பு உட்கொள்ளலை ஒரு நாளைக்கு 3 கிராமுக்குள் வைத்திருங்கள்.",
        "severity": "caution", "precedence": 5, "source_reference": "ICMR 2018 Sec 7.1.1",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_005", "module_id": "B2", "content_type": "tip",
        "condition_tags": ["duration_gt_5"],
        "text_en": "Since you have had diabetes for more than 5 years, complication surveillance and annual screening are especially important.",
        "text_ta": "உங்களுக்கு 5 ஆண்டுகளுக்கும் மேலாக நீரிழிவு இருப்பதால், சிக்கல்களை கண்காணிப்பதும் ஆண்டுதோறும் பரிசோதனை செய்வதும் மிக முக்கியம்.",
        "severity": "info", "precedence": 8, "source_reference": "ICMR 2018 Sec 7.1.2",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_006", "module_id": "B2", "content_type": "warning",
        "condition_tags": ["uses_sulfonylurea"],
        "text_en": "Take your sulfonylurea 15-30 minutes before the meal, and never take it if that meal will be skipped -- it can cause low sugar, especially in older adults.",
        "text_ta": "சல்போனைல்யூரியா மருந்தை உணவுக்கு 15-30 நிமிடங்களுக்கு முன் எடுத்துக் கொள்ளுங்கள். அந்த உணவை தவிர்க்கப் போகிறீர்கள் என்றால் மருந்தை எடுத்துக் கொள்ள வேண்டாம் -- இது குறிப்பாக வயதானவர்களுக்கு சர்க்கரை அளவு குறையக் காரணமாகலாம்.",
        "severity": "caution", "precedence": 3, "source_reference": "ICMR 2018 Sec 5.1",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_007", "module_id": "B2", "content_type": "tip",
        "condition_tags": ["uses_insulin"],
        "text_en": "Store insulin at 2-8C in the lower door of the refrigerator, never the freezer. Rotate injection sites within one area. Change needles after 3-4 uses. Never share your insulin pen or needles.",
        "text_ta": "இன்சுலினை குளிர்சாதன பெட்டியின் கீழ் கதவில், 2-8 டிகிரி செல்சியஸில் வையுங்கள் -- ஃப்ரீசரில் வைக்க வேண்டாம். ஊசி போடும் இடத்தை ஒரே பகுதியில் மாற்றி மாற்றி போடுங்கள். 3-4 முறை பயன்படுத்திய பிறகு ஊசியை மாற்றுங்கள். உங்கள் இன்சுலின் பேனா அல்லது ஊசியை மற்றவர்களுடன் பகிர வேண்டாம்.",
        "severity": "info", "precedence": 5, "source_reference": "ICMR 2018 Sec 5.1",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_008", "module_id": "B2", "content_type": "warning",
        "condition_tags": ["herbal_use"],
        "text_en": "You mentioned a siddha, ayurvedic, or herbal medicine. Please tell your doctor -- herb-drug interactions are possible. This is not an endorsement or a prohibition.",
        "text_ta": "நீங்கள் சித்த, ஆயுர்வேத அல்லது மூலிகை மருந்து குறிப்பிட்டீர்கள். தயவுசெய்து உங்கள் மருத்துவரிடம் சொல்லுங்கள் -- மூலிகை-மருந்து இடையே எதிர்வினை ஏற்படக்கூடும். இது ஒரு பரிந்துரையும் அல்ல, தடையும் அல்ல.",
        "severity": "caution", "precedence": 6, "source_reference": "ICMR 2018 Sec 8.5.3",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_009", "module_id": "B2", "content_type": "reminder",
        "condition_tags": ["follow_up_gap"],
        "text_en": "It has been more than 3 months since your last clinical review. Please schedule a visit.",
        "text_ta": "உங்கள் கடைசி மருத்துவ பரிசோதனைக்குப் பிறகு 3 மாதங்களுக்கும் மேலாகிவிட்டது. தயவுசெய்து ஒரு வருகையை ஏற்பாடு செய்யுங்கள்.",
        "severity": "caution", "precedence": 7, "source_reference": "ICMR 2018 Sec 10.1",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_010", "module_id": "B2", "content_type": "reminder",
        "condition_tags": ["eye_screening_overdue"],
        "text_en": "Your eye (dilated retinal) check is overdue -- it is recommended once a year.",
        "text_ta": "உங்கள் கண் (விழித்திரை விரிவாக்க) பரிசோதனை தாமதமாகிவிட்டது -- இது ஆண்டுக்கு ஒரு முறை பரிந்துரைக்கப்படுகிறது.",
        "severity": "info", "precedence": 9, "source_reference": "ICMR 2018 Sec 7.2.5",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_011", "module_id": "B2", "content_type": "reminder",
        "condition_tags": ["foot_screening_overdue"],
        "text_en": "Your foot examination is overdue -- it is recommended at every clinic visit, at least yearly.",
        "text_ta": "உங்கள் கால் பரிசோதனை தாமதமாகிவிட்டது -- இது ஒவ்வொரு மருத்துவமனை வருகையிலும், குறைந்தது ஆண்டுக்கு ஒரு முறையாவது பரிந்துரைக்கப்படுகிறது.",
        "severity": "info", "precedence": 9, "source_reference": "ICMR 2018 Sec 7.2.6",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_012", "module_id": "B2", "content_type": "reminder",
        "condition_tags": ["renal_screening_overdue"],
        "text_en": "Your urine albumin and creatinine test is overdue -- it is recommended once a year.",
        "text_ta": "உங்கள் சிறுநீர் ஆல்புமின் மற்றும் கிரியாட்டினின் பரிசோதனை தாமதமாகிவிட்டது -- இது ஆண்டுக்கு ஒரு முறை பரிந்துரைக்கப்படுகிறது.",
        "severity": "info", "precedence": 9, "source_reference": "ICMR 2018 Sec 7.2.7",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_013", "module_id": "B3", "content_type": "warning",
        "condition_tags": ["neuropathy", "foot_risk_moderate"],
        "text_en": "Never walk barefoot, even indoors. Wear MCR or well-fitting footwear with dry socks. Check your feet daily, including between the toes. Walk only on flat, even ground.",
        "text_ta": "வீட்டிற்குள் கூட வெறும் காலுடன் நடக்க வேண்டாம். MCR அல்லது நன்றாகப் பொருந்தும் காலணிகளை உலர்ந்த சாக்ஸுடன் அணியுங்கள். ஒவ்வொரு நாளும் கால்களை, விரல்களுக்கு இடையேயும் சேர்த்து பரிசோதியுங்கள். சமமான, தட்டையான தரையில் மட்டுமே நடக்கவும்.",
        "severity": "caution", "precedence": 2, "source_reference": "ICMR 2018 Sec 6.3",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_014", "module_id": "B3", "content_type": "warning",
        "condition_tags": ["foot_risk_active_foot_disease"],
        "text_en": "Non-weight-bearing activity only, and referral to a foot care service within 24 hours.",
        "text_ta": "எடை தாங்காத செயல்பாடுகள் மட்டுமே செய்யவும். 24 மணி நேரத்திற்குள் கால் பராமரிப்பு மையத்திற்கு அனுப்பப்பட வேண்டும்.",
        "severity": "medical_clearance", "precedence": 1, "source_reference": "ICMR 2018 Sec 8.3",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_015", "module_id": "B3", "content_type": "warning",
        "condition_tags": ["retinopathy"],
        "text_en": "Avoid vigorous activity, head-down postures, and any jarring or head-impact activity.",
        "text_ta": "கடுமையான உடற்பயிற்சி, தலை கீழாக இருக்கும் தோரணைகள் மற்றும் அதிர்வு அல்லது தலையில் அடி படும் செயல்பாடுகளைத் தவிர்க்கவும்.",
        "severity": "caution", "precedence": 2, "source_reference": "ICMR 2018 Sec 8.5",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_016", "module_id": "B3", "content_type": "warning",
        "condition_tags": ["nephropathy"],
        "text_en": "Medical clearance is needed before increasing activity. No protein or sodium target is set here -- that defers to your treating team.",
        "text_ta": "உடற்செயல்பாட்டை அதிகரிக்கும் முன் மருத்துவ அனுமதி தேவை. புரதம் அல்லது சோடியம் இலக்கு இங்கு நிர்ணயிக்கப்படவில்லை -- அது உங்கள் சிகிச்சை குழுவின் முடிவு.",
        "severity": "medical_clearance", "precedence": 1, "source_reference": "ICMR 2018 Sec 8.6",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_017", "module_id": "B3", "content_type": "warning",
        "condition_tags": ["cad"],
        "text_en": "Medical clearance is needed before moderate or vigorous exercise. Light activity may continue. Any chest pain routes to the safety module immediately.",
        "text_ta": "மிதமான அல்லது கடுமையான உடற்பயிற்சிக்கு முன் மருத்துவ அனுமதி தேவை. இலேசான செயல்பாடுகளை தொடரலாம். மார்பு வலி ஏற்பட்டால் உடனடியாக பாதுகாப்பு பிரிவுக்கு அனுப்பப்படும்.",
        "severity": "medical_clearance", "precedence": 1, "source_reference": "ICMR 2018 Sec 8.7.3",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_018", "module_id": "B3", "content_type": "tip",
        "condition_tags": ["tobacco"],
        "text_en": "Cessation advice will be repeated at every check-in.",
        "text_ta": "புகையிலை நிறுத்துவது குறித்த ஆலோசனை ஒவ்வொரு சரிபார்ப்பிலும் மீண்டும் சொல்லப்படும்.",
        "severity": "info", "precedence": 10, "source_reference": "ICMR 2018 Sec 8.7.4",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_019", "module_id": "B3", "content_type": "tip",
        "condition_tags": ["alcohol"],
        "text_en": "Alcohol is best avoided, and never on an empty stomach -- it can cause low sugar. It is not counted as part of the meal plan.",
        "text_ta": "மது தவிர்ப்பது நல்லது, வெறும் வயிற்றில் ஒருபோதும் அருந்த வேண்டாம் -- இது சர்க்கரை அளவைக் குறைக்கக் காரணமாகலாம். இது உணவுத் திட்டத்தின் ஒரு பகுதியாக கணக்கிடப்படாது.",
        "severity": "info", "precedence": 10, "source_reference": "ICMR 2018 Sec 8.7.4",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_020", "module_id": "C", "content_type": "script", "release_tag": "sick_day",
        "condition_tags": ["sick_day"],
        "text_en": "You mentioned fever or vomiting. Test your sugar more often, keep taking your tablets unless your doctor says otherwise, drink fluids, and seek care if you cannot keep fluids down or your sugar stays high.",
        "text_ta": "நீங்கள் காய்ச்சல் அல்லது வாந்தி இருப்பதாக சொன்னீர்கள். சர்க்கரை அளவை அடிக்கடி சோதியுங்கள், மருத்துவர் சொல்லாத வரை மருந்துகளை தொடர்ந்து எடுத்துக் கொள்ளுங்கள், நிறைய தண்ணீர் அருந்துங்கள். திரவங்களை வயிற்றில் வைத்திருக்க முடியாவிட்டாலோ சர்க்கரை அளவு அதிகமாகவே இருந்தாலோ உடனே மருத்துவரை அணுகுங்கள்.",
        "severity": "caution", "precedence": 4, "source_reference": "ICMR 2018 Sec 8.1.2",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_021", "module_id": "C", "content_type": "script", "release_tag": "festival_fasting",
        "condition_tags": ["festival_fasting"],
        "text_en": "You mentioned an upcoming function or fasting. Plan your meal timing with your medicine timing, and check your sugar more often on that day. Discuss any planned fasting with your doctor first.",
        "text_ta": "நீங்கள் வரவிருக்கும் விழா அல்லது நோன்பு குறித்து சொன்னீர்கள். உங்கள் உணவு நேரத்தை மருந்து நேரத்துடன் ஒத்திசைத்து திட்டமிடுங்கள், அன்று சர்க்கரை அளவை அடிக்கடி சோதியுங்கள். நோன்பு இருக்கும் திட்டம் இருந்தால் முதலில் உங்கள் மருத்துவரிடம் விவாதியுங்கள்.",
        "severity": "caution", "precedence": 4, "source_reference": "ICMR 2018 Sec 6.2.3",
        "review_status": "approved",
    },
    {
        "id": "CONTENT_022", "module_id": "D", "content_type": "script",
        "condition_tags": [
            "risk_red", "chest_pain", "breathlessness_at_rest", "severe_giddiness", "fainting", "confusion",
            "repeated_vomiting", "cannot_keep_fluids", "foot_blackening", "spreading_redness", "foul_smell",
            "sugar_below_70", "sugar_above_400", "sudden_vision_loss", "reduced_urine_output",
        ],
        "text_en": "This needs urgent attention. Please stop and go to the nearest health facility now. No further self-care advice will be given until you have been seen.",
        "text_ta": "இது உடனடி கவனிப்பு தேவைப்படுகிறது. தயவுசெய்து நிறுத்திவிட்டு இப்போதே அருகிலுள்ள மருத்துவமனைக்குச் செல்லுங்கள். நீங்கள் பரிசோதிக்கப்படும் வரை மேலும் சுய-பராமரிப்பு ஆலோசனை வழங்கப்படாது.",
        "severity": "emergency", "precedence": 1, "source_reference": "ICMR 2018 Sec 8.1",
        "review_status": "approved",
    },
]


async def seed_data():
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(CareContentRule))
        if existing.scalars().first():
            print("CareContentRule table already has data. Skipping seed.")
            return

        for rule_data in RULES:
            rule_data.setdefault("release_tag", None)
            session.add(CareContentRule(**rule_data))

        await session.commit()
        print(f"Seeded {len(RULES)} care content rules.")


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_data()


if __name__ == "__main__":
    asyncio.run(main())
