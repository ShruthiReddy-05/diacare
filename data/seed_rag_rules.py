import asyncio
import sys
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal, Base, engine
from models.rag_rule import ExerciseRagRule

# Define the seed rules
RULES = [
    {
        "id": "RAG_001",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["overweight", "obese"],
        "contraindication_tags": ["high_impact"],
        "allowed_exercise_tags": ["walking", "cycling", "water_exercise", "low_impact"],
        "prohibited_exercise_tags": ["high_impact_aerobics", "running_jumping"],
        "recommendation": "If overweight or obese: Choose low-impact exercises such as walking, cycling, or water exercises to reduce stress on joints. Start slowly and increase activity gradually to avoid excessive fatigue.",
        "rationale": "Overweight/obesity increases joint stress, making high-impact activities riskier. Low-impact options protect joints.",
        "severity": "info",
        "precedence": 5
    },
    {
        "id": "RAG_002",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["duration_gt_5"],
        "contraindication_tags": [],
        "allowed_exercise_tags": [],
        "prohibited_exercise_tags": [],
        "recommendation": "Since you have had diabetes for more than 5 years, please monitor your fatigue and glucose response closely during and after exercising.",
        "rationale": "Longer diabetes duration is associated with higher rates of subclinical complications; careful self-monitoring is advised.",
        "severity": "info",
        "precedence": 4
    },
    {
        "id": "RAG_003",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["uses_insulin"],
        "contraindication_tags": ["empty_stomach_exercise"],
        "allowed_exercise_tags": [],
        "prohibited_exercise_tags": [],
        "recommendation": "Since you are on insulin, always carry a fast-acting snack or glucose source (like glucose tablets or juice). Avoid exercising on an empty stomach and monitor your blood sugar before and after exercise.",
        "rationale": "Insulin use drastically increases hypoglycemia risk. Food intake and sugar source availability are essential safety measures.",
        "severity": "caution",
        "precedence": 4
    },
    {
        "id": "RAG_004",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["neuropathy"],
        "contraindication_tags": ["barefoot_exercise", "high_impact", "uneven_terrain"],
        "allowed_exercise_tags": ["walking_even_ground", "stationary_cycling", "seated_exercises"],
        "prohibited_exercise_tags": ["barefoot", "long_distance_hiking", "jogging", "uneven_terrain_walking"],
        "recommendation": "Avoid barefoot exercise and high-impact activity. Use appropriate protective footwear and socks that keep feet dry. Check your feet daily for cuts, blisters, redness, or swelling. Avoid long-distance hiking, jogging, or walking on uneven terrain. Do not perform physical activities exceeding your balance capabilities.",
        "rationale": "Loss of protective sensation in neuropathy increases risk of unnoticed foot injury, infection, and ulceration. Balance may also be impaired.",
        "severity": "caution",
        "precedence": 3
    },
    {
        "id": "RAG_005",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["eye_disease"],
        "contraindication_tags": ["vigorous", "head_down", "head_impact"],
        "allowed_exercise_tags": ["leisure_walking", "stationary_cycling", "seated_strength"],
        "prohibited_exercise_tags": ["head_down_yoga", "gymnastics", "heavy_lifting", "contact_sports"],
        "recommendation": "Avoid vigorous-intensity physical activity. Do not engage in activities that involve head-down positions (e.g. certain yoga poses) or cause head impacts.",
        "rationale": "Vigorous activity and head-down positions increase intraocular pressure, raising risk of vitreous hemorrhage or retinal detachment in diabetic retinopathy.",
        "severity": "caution",
        "precedence": 3
    },
    {
        "id": "RAG_006",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["kidney_disease"],
        "contraindication_tags": ["vigorous"],
        "allowed_exercise_tags": ["light_activity", "leisure_walking"],
        "prohibited_exercise_tags": ["vigorous_intensity"],
        "recommendation": "Please obtain medical clearance from your doctor before starting moderate-to-vigorous physical activity.",
        "rationale": "Kidney disease warrants medical clearance due to potential cardiovascular comorbidities and altered electrolyte/fluid dynamics during exercise.",
        "severity": "medical_clearance",
        "precedence": 3
    },
    {
        "id": "RAG_007",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["foot_wounds"],
        "contraindication_tags": ["weight_bearing", "prolonged_walking"],
        "allowed_exercise_tags": ["chair_exercises", "seated_strength", "non_weight_bearing_exercise"],
        "prohibited_exercise_tags": ["walking", "jogging", "standing_exercises"],
        "recommendation": "Non-weight-bearing exercises are preferred. Use chair-based or seated exercises. Avoid walking or standing exercises until your foot wound or ulcer has been fully reviewed and cleared by a doctor.",
        "rationale": "Weight-bearing exercises delay wound healing and can worsen diabetic foot ulcers. Seated/non-weight-bearing options are safe fallbacks.",
        "severity": "caution",
        "precedence": 3
    },
    {
        "id": "RAG_008",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["hypoglycemia_history"],
        "contraindication_tags": [],
        "allowed_exercise_tags": [],
        "prohibited_exercise_tags": [],
        "recommendation": "Always carry glucose tablets, juice, or snacks during activity. Monitor your blood sugar regularly before and after exercise to prevent sudden drops.",
        "rationale": "A history of exercise-induced hypoglycemia indicates high glycemic sensitivity. Frequent glucose checks and ready access to fast carbs are vital.",
        "severity": "caution",
        "precedence": 4
    },
    {
        "id": "RAG_009",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["sedentary_gt_4"],
        "contraindication_tags": [],
        "allowed_exercise_tags": ["NEAT_breaks", "stretching"],
        "prohibited_exercise_tags": [],
        "recommendation": "Avoid sitting continuously for long periods. Stand up and move for 2-3 minutes every 30-60 minutes. Include short walks or gentle shoulder/neck stretches during work or screen time.",
        "rationale": "Sedentary behavior for >=4 hours increases cardiometabolic risk. Active movement breaks improve glycemic levels and joint mobility.",
        "severity": "info",
        "precedence": 5
    },
    {
        "id": "RAG_010",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["par_q_clearance"],
        "contraindication_tags": ["moderate_intensity", "vigorous_intensity"],
        "allowed_exercise_tags": ["light_activity", "slow_walking", "gentle_stretching"],
        "prohibited_exercise_tags": ["brisk_walking", "running", "heavy_resistance"],
        "recommendation": "Medical clearance is recommended before starting moderate or vigorous exercise because you answered YES to one or more safety questions on the PAR-Q. Please engage only in light activity (like slow walking or gentle stretching) until reviewed by your doctor.",
        "rationale": "A positive response on the PAR-Q indicates underlying cardiovascular, musculoskeletal, or balance concerns that require clinical approval for moderate-to-vigorous efforts.",
        "severity": "medical_clearance",
        "precedence": 2
    },
    {
        "id": "RAG_011",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["low_confidence"],
        "contraindication_tags": [],
        "allowed_exercise_tags": [],
        "prohibited_exercise_tags": [],
        "recommendation": "Start with smaller, highly achievable goals (such as a 5-10 minute comfortable walk) to build your confidence and physical activity habit gradually.",
        "rationale": "Low confidence benefits from early positive mastery experiences. Low-demand, high-success tasks support habit formation.",
        "severity": "info",
        "precedence": 7
    },
    {
        "id": "RAG_012",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["barrier_time"],
        "contraindication_tags": [],
        "allowed_exercise_tags": ["short_bouts", "home_exercise"],
        "prohibited_exercise_tags": [],
        "recommendation": "If you lack time, break your physical activity into short 10-minute bouts throughout the day (e.g. three 10-minute walks are as effective as one 30-minute session). Try home-based exercise routines.",
        "rationale": "Accumulating physical activity in short sessions overcomes time barriers while providing similar cardiometabolic benefits.",
        "severity": "info",
        "precedence": 7
    },
    {
        "id": "RAG_013",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["barrier_pain_fatigue"],
        "contraindication_tags": [],
        "allowed_exercise_tags": ["low_intensity", "seated_stretching"],
        "prohibited_exercise_tags": [],
        "recommendation": "When feeling pain or fatigue, reduce the exercise intensity and duration. Modify the exercises to gentler modes, such as seated stretching, slow walking, or joint rotations.",
        "rationale": "Reducing load during symptom flares supports long-term adherence without causing musculoskeletal strain or exhaustion.",
        "severity": "info",
        "precedence": 7
    },
    {
        "id": "RAG_014",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["poor_sleep_stress"],
        "contraindication_tags": ["high_intensity"],
        "allowed_exercise_tags": ["relaxation", "yoga", "stretching", "low_intensity_walking"],
        "prohibited_exercise_tags": [],
        "recommendation": "When sleep is poor or stress is high, lower your initial exercise intensity. Focus on relaxation, gentle stretching, breathing exercises, or restorative yoga to promote recovery.",
        "rationale": "Elevated stress and poor sleep compromise physical recovery. Light, restorative movement lowers cortisol and avoids overtraining.",
        "severity": "info",
        "precedence": 8
    },
    {
        "id": "RAG_015",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["junk_food"],
        "contraindication_tags": [],
        "allowed_exercise_tags": [],
        "prohibited_exercise_tags": [],
        "recommendation": "Support your exercise energy by reinforcing healthy eating behaviors. Focus on drinking plenty of water and eating whole foods rich in fiber.",
        "rationale": "Frequent junk food impairs energy and metabolic recovery. Proper hydration and fiber-rich foods stabilize glucose levels during activity.",
        "severity": "info",
        "precedence": 8
    },
    {
        "id": "RAG_016",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["plan_a"],
        "contraindication_tags": [],
        "allowed_exercise_tags": ["comfortable_walking", "low_impact"],
        "prohibited_exercise_tags": [],
        "recommendation": "Beginner Aerobic Plan A: Walk for 10-15 minutes on at least 5 days per week. Walk at a comfortable, leisurely pace where you can easily talk. Increase the duration by 5 minutes each week as you feel comfortable, working toward a goal of 30 minutes per day.",
        "rationale": "Plan A is designed for inactive individuals, obesity, or complications, providing a gradual, safe ramp-up.",
        "severity": "info",
        "precedence": 6
    },
    {
        "id": "RAG_017",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["plan_b"],
        "contraindication_tags": [],
        "allowed_exercise_tags": ["brisk_walking", "cycling", "dancing", "badminton"],
        "prohibited_exercise_tags": [],
        "recommendation": "Active Aerobic Plan B: Walk briskly or engage in active preferred exercise (such as cycling, dancing, or badminton) for 30 minutes per day on at least 5 days per week. The intensity should make your breathing a little faster, but you should still be able to hold a conversation.",
        "rationale": "Plan B is a standard FITT physical activity guideline for type 2 diabetes when no severe complications or risks are present.",
        "severity": "info",
        "precedence": 6
    },
    {
        "id": "RAG_018",
        "source_type": "at4_logic",
        "source_name": "AT_4 Chatbot Conversation Logic Draft",
        "source_sheet": "Sheet1",
        "condition_tags": ["strength"],
        "contraindication_tags": [],
        "allowed_exercise_tags": ["sit_to_stand", "wall_pushups", "toe_stands", "resistance_bands", "water_bottle_weights"],
        "prohibited_exercise_tags": [],
        "recommendation": "Muscle Strengthening: Perform exercises like chair sit-to-stands, wall push-ups, standing on toes while holding a chair, resistance band moves, or lifting water bottles. Aim for 1-2 sets of 10-15 repetitions on 2-3 non-consecutive days per week. Stretch for 5-10 minutes after physical activity.",
        "rationale": "Resistance training increases insulin sensitivity and muscle mass, key for glycemic control. Warm-up/cool-down stretches preserve flexibility.",
        "severity": "info",
        "precedence": 6
    }
]

async def seed_data():
    async with AsyncSessionLocal() as session:
        # Check if rules are already present
        result = await session.execute(select(ExerciseRagRule))
        existing_rules = result.scalars().all()
        if existing_rules:
            print(f"Database already has {len(existing_rules)} RAG rules. Skipping seeding.")
            return
            
        print("Seeding exercise RAG rules...")
        for rule_dict in RULES:
            rule = ExerciseRagRule(**rule_dict)
            rule.review_status = "approved"
            session.add(rule)
        await session.commit()
        print("Exercise RAG rules seeded successfully.")

if __name__ == "__main__":
    # Ensure tables are created first
    async def main():
        async with engine.begin() as conn:
            # We import all models to bind them to Base metadata
            import backend.models
            await conn.run_sync(Base.metadata.create_all)
        await seed_data()
        
    asyncio.run(main())
