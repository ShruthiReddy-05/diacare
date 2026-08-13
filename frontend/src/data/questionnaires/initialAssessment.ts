import type { QuestionnaireDefinition } from '../../domain/types';

export const initialAssessmentQuestionnaire: QuestionnaireDefinition = {
  id: "initial_assessment",
  version: "2.0.0",
  status: "active",
  title: {
    en: "Initial Diabetes Activity Assessment",
    ta: "ஆரம்ப நீரிழிவு செயல்பாடு மதிப்பீடு"
  },
  modules: [
    {
      id: "mod_onboarding",
      title: { en: "Onboarding", ta: "அறிமுகம்" },
      purpose: "Welcome patient and verify intent to begin.",
      questions: [
        {
          id: "shall_we_begin",
          moduleId: "mod_onboarding",
          prompt: {
            en: "Vanakkam! I am your DiaFit coach. I can help you manage your diabetes through simple lifestyle changes. This assessment takes around 5-7 minutes. Would you like to begin?",
            ta: "வணக்கம்! நான் உங்கள் டயாஃபிட் (DiaFit) பயிற்சியாளர். எளிய வாழ்க்கை முறை மாற்றங்கள் மூலம் உங்கள் நீரிழிவு நோயை நிர்வகிக்க நான் உங்களுக்கு உதவ முடியும். இந்த மதிப்பீடு சுமார் 5-7 நிமிடங்கள் ஆகும். நாம் தொடங்கலாமா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes, let's begin", ta: "ஆம், தொடங்கலாம்" } },
            { value: "no", label: { en: "No, later", ta: "இல்லை, பிறகு செய்கிறேன்" } }
          ],
          required: true,
          saveAs: "shallBegin"
        }
      ]
    },
    {
      id: "mod_basic_profile",
      title: { en: "Basic Profile", ta: "அடிப்படை விவரக்குறிப்பு" },
      purpose: "Collect basic demographics for BMI and metabolic ranges.",
      questions: [
        {
          id: "age",
          moduleId: "mod_basic_profile",
          prompt: {
            en: "How old are you?",
            ta: "உங்கள் வயது என்ன?"
          },
          inputType: "number",
          min: 18,
          max: 100,
          required: true,
          saveAs: "age"
        },
        {
          id: "gender",
          moduleId: "mod_basic_profile",
          prompt: {
            en: "What is your gender?",
            ta: "உங்கள் பாலினம் என்ன?"
          },
          inputType: "single_choice",
          options: [
            { value: "male", label: { en: "Male", ta: "ஆண்" } },
            { value: "female", label: { en: "Female", ta: "பெண்" } },
            { value: "other", label: { en: "Other", ta: "மற்றவை" } }
          ],
          required: true,
          saveAs: "gender"
        },
        {
          id: "height_weight",
          moduleId: "mod_basic_profile",
          prompt: {
            en: "Please enter your height and weight. This helps us calculate your Body Mass Index (BMI).",
            ta: "உங்கள் உயரம் மற்றும் எடையை உள்ளிடவும். இது உங்கள் உடல் நிறை குறியீட்டை (BMI) கணக்கிட உதவுகிறது."
          },
          inputType: "height_weight",
          required: true,
          saveAs: "height_weight" // heightCm and weightKg will be extracted
        }
      ]
    },
    {
      id: "mod_diabetes_profile",
      title: { en: "Diabetes Profile", ta: "நீரிழிவு நோய் விவரக்குறிப்பு" },
      purpose: "Understand duration, control, and medications.",
      questions: [
        {
          id: "duration",
          moduleId: "mod_diabetes_profile",
          prompt: {
            en: "How long have you had diabetes (in years)?",
            ta: "உங்களுக்கு நீரிழிவு நோய் ஏற்பட்டு எத்தனை ஆண்டுகள் ஆகிறது?"
          },
          inputType: "number",
          min: 0,
          max: 60,
          required: true,
          saveAs: "durationYears"
        },
        {
          id: "knows_hba1c",
          moduleId: "mod_diabetes_profile",
          prompt: {
            en: "Do you know your latest HbA1c reading?",
            ta: "உங்களின் சமீபத்திய HbA1c அளவு உங்களுக்குத் தெரியுமா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "knowsHbA1c"
        },
        {
          id: "hba1c",
          moduleId: "mod_diabetes_profile",
          prompt: {
            en: "Please enter your last HbA1c reading (%):",
            ta: "உங்கள் கடைசி HbA1c அளவை (%) உள்ளிடவும்:"
          },
          inputType: "decimal",
          min: 3,
          max: 20,
          required: false,
          saveAs: "hba1c",
          branching: [
            { dependsOn: "knows_hba1c", equals: "no", nextQuestionId: "knows_fasting" }
          ]
        },
        {
          id: "knows_fasting",
          moduleId: "mod_diabetes_profile",
          prompt: {
            en: "Do you know your latest Fasting Blood Sugar reading?",
            ta: "உங்களின் சமீபத்திய வெற்று வயிற்று இரத்த சர்க்கரை அளவு உங்களுக்குத் தெரியுமா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "knowsFasting",
          branching: [
            { dependsOn: "knows_hba1c", equals: "yes", nextQuestionId: "medications" }
          ]
        },
        {
          id: "fasting_sugar",
          moduleId: "mod_diabetes_profile",
          prompt: {
            en: "Please enter your Fasting Blood Sugar reading (mg/dL):",
            ta: "உங்கள் வெற்று வயிற்று இரத்த சர்க்கரை அளவை (mg/dL) உள்ளிடவும்:"
          },
          inputType: "number",
          min: 40,
          max: 500,
          required: false,
          saveAs: "fastingSugar",
          branching: [
            { dependsOn: "knows_fasting", equals: "no", nextQuestionId: "medications" }
          ]
        },
        {
          id: "medications",
          moduleId: "mod_diabetes_profile",
          prompt: {
            en: "What diabetes medications do you take currently?",
            ta: "தற்போது நீங்கள் என்ன நீரிழிவு மருந்துகளை உட்கொள்கிறீர்கள்?"
          },
          inputType: "single_choice",
          options: [
            { value: "medicines", label: { en: "Medicines only", ta: "மருந்துகள் மட்டும்" } },
            { value: "insulin", label: { en: "Insulin only", ta: "இன்சுலின் மட்டும்" } },
            { value: "both", label: { en: "Both medicines and insulin", ta: "மருந்துகள் மற்றும் இன்சுலின் இரண்டும்" } },
            { value: "none", label: { en: "No medications", ta: "மருந்துகள் இல்லை" } }
          ],
          required: true,
          saveAs: "medications"
        }
      ]
    },
    {
      id: "mod_complications",
      title: { en: "Complications", ta: "உடல்நல சிக்கல்கள்" },
      purpose: "Screen for neuropathic, visual, cardiac, renal, and diabetic complications.",
      questions: [
        {
          id: "hypertension",
          moduleId: "mod_complications",
          prompt: {
            en: "Do you have high blood pressure (hypertension)?",
            ta: "உங்களுக்கு உயர் இரத்த அழுத்தம் (BP) உள்ளதா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "hasHypertension"
        },
        {
          id: "neuropathy",
          moduleId: "mod_complications",
          prompt: {
            en: "Do you experience numbness, tingling, or burning sensations in your feet?",
            ta: "உங்கள் பாதங்களில் மரத்துப்போதல், ஊசி குத்துவது போன்ற உணர்வு அல்லது எரிச்சல் ஏற்படுகிறதா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "hasNeuropathySymptoms"
        },
        {
          id: "eye_disease",
          moduleId: "mod_complications",
          prompt: {
            en: "Have you been diagnosed with diabetic eye disease (retinopathy)?",
            ta: "உங்களுக்கு நீரிழிவு கண் நோய் (ரெட்டினோபதி) இருப்பதாகக் கண்டறியப்பட்டுள்ளதா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "hasEyeDisease"
        },
        {
          id: "kidney_disease",
          moduleId: "mod_complications",
          prompt: {
            en: "Do you have diabetic kidney disease?",
            ta: "உங்களுக்கு நீரிழிவு சிறுநீரக நோய் உள்ளதா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "hasKidneyDisease"
        },
        {
          id: "foot_wound",
          moduleId: "mod_complications",
          prompt: {
            en: "Do you currently have any foot wounds, sores, or ulcers?",
            ta: "உங்களுக்கு தற்போது பாதங்களில் காயங்கள், புண்கள் அல்லது கொப்புளங்கள் ஏதேனும் உள்ளதா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "hasFootWoundOrUlcer"
        },
        {
          id: "hypo_history",
          moduleId: "mod_complications",
          prompt: {
            en: "Have you experienced low blood sugar (hypoglycemia) during or immediately after exercise before?",
            ta: "இதற்கு முன்பு உடற்பயிற்சியின் போது அல்லது உடற்பயிற்சி செய்த உடனே உங்களுக்கு குறைந்த இரத்த சர்க்கரை (ஹைப்போகிளைசீமியா) ஏற்பட்டுள்ளதா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "hasExerciseHypoglycemiaHistory"
        },
        {
          id: "fall_history",
          moduleId: "mod_complications",
          prompt: {
            en: "Have you had a fall in the past year?",
            ta: "கடந்த ஒரு வருடத்தில் நீங்கள் கீழே விழுந்தது உண்டா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "hasFallHistory"
        }
      ]
    },
    {
      id: "mod_physical_activity",
      title: { en: "Physical Activity (IPAQ-SF)", ta: "உடல் செயல்பாடு (IPAQ-SF)" },
      purpose: "Assess physical activity using the International Physical Activity Questionnaire (Short Form).",
      questions: [
        {
          id: "vigorous_days",
          moduleId: "mod_physical_activity",
          prompt: {
            en: "During the last 7 days, on how many <strong class=\"hi-vig\">days</strong> did you do <strong class=\"hi-vig\">vigorous</strong> physical activities like heavy lifting, digging, aerobics, or fast cycling?",
            ta: "கடந்த 7 நாட்களில், கனமான பொருட்களை தூக்குவது, தோண்டுவது, ஏரோபிக்ஸ் அல்லது வேகமாக சைக்கிள் ஓட்டுவது போன்ற <strong class=\"hi-vig\">கடுமையான</strong> உடல் செயல்பாடுகளை எத்தனை <strong class=\"hi-vig\">நாட்கள்</strong> செய்தீர்கள்?"
          },
          ttsPrompt: {
            en: "During the last 7 days, on how many days did you do vigorous physical activities like heavy lifting, digging, aerobics, or fast cycling?",
            ta: "கடந்த 7 நாட்களில், கனமான பொருட்களை தூக்குவது, தோண்டுவது, ஏரோபிக்ஸ் அல்லது வேகமாக சைக்கிள் ஓட்டுவது போன்ற கடுமையான உடல் செயல்பாடுகளை எத்தனை நாட்கள் செய்தீர்கள்?"
          },
          inputType: "number",
          min: 0,
          max: 7,
          required: true,
          saveAs: "vigorousDays",
          validation: [
            { type: 'min', value: 0, message: { en: 'Enter a number between 0 and 7. This asks for DAYS (0–7), not minutes. Example: if you did vigorous activity on 3 days, enter 3.', ta: '0 முதல் 7 வரையிலான எண்ணை உள்ளிடவும். இது நாட்களை (0–7) கேட்கிறது, நிமிடங்களை அல்ல. எ.கா: 3 நாட்கள் கடுமையான செயல்பாடு செய்தால், 3 ஐ உள்ளிடவும்.' } },
            { type: 'max', value: 7, message: { en: 'Enter a number between 0 and 7. This asks for DAYS (0–7), not minutes. Example: if you did vigorous activity on 3 days, enter 3.', ta: '0 முதல் 7 வரையிலான எண்ணை உள்ளிடவும். இது நாட்களை (0–7) கேட்கிறது, நிமிடங்களை அல்ல. எ.கா: 3 நாட்கள் கடுமையான செயல்பாடு செய்தால், 3 ஐ உள்ளிடவும்.' } }
          ]
        },
        {
          id: "vigorous_minutes",
          moduleId: "mod_physical_activity",
          prompt: {
            en: "How many <strong class=\"hi-vig\">minutes</strong> did you usually spend doing <strong class=\"hi-vig\">vigorous</strong> activities on one of those days?",
            ta: "அந்த நாட்களில் ஒரு நாளில் பொதுவாக எத்தனை <strong class=\"hi-vig\">நிமிடங்கள்</strong> <strong class=\"hi-vig\">கடுமையான</strong> உடல் செயல்பாடுகளில் ஈடுபட்டீர்கள்?"
          },
          ttsPrompt: {
            en: "How many minutes did you usually spend doing vigorous physical activities on one of those days?",
            ta: "அந்த நாட்களில் ஒரு நாளில் பொதுவாக எத்தனை நிமிடங்கள் கடுமையான உடல் செயல்பாடுகளில் ஈடுபட்டீர்கள்?"
          },
          inputType: "number",
          min: 0,
          max: 480,
          required: true,
          saveAs: "vigorousMinutes",
          validation: [
            { type: 'min', value: 0, message: { en: 'Enter a number between 0 and 480 minutes.', ta: '0 முதல் 480 நிமிடங்கள் வரையிலான எண்ணை உள்ளிடவும்.' } },
            { type: 'max', value: 480, message: { en: 'Enter a number between 0 and 480 minutes.', ta: '0 முதல் 480 நிமிடங்கள் வரையிலான எண்ணை உள்ளிடவும்.' } }
          ]
        },
        {
          id: "moderate_days",
          moduleId: "mod_physical_activity",
          prompt: {
            en: "During the last 7 days, on how many <strong class=\"hi-mod\">days</strong> did you do <strong class=\"hi-mod\">moderate</strong> physical activities like carrying light loads, bicycling at a regular pace, or doubles tennis? Do not include walking.",
            ta: "கடந்த 7 நாட்களில், இலகுவான பொருட்களை சுமந்து செல்வது, சாதாரண வேகத்தில் சைக்கிள் ஓட்டுவது அல்லது இரட்டையர் டென்னிஸ் போன்ற <strong class=\"hi-mod\">மிதமான</strong> உடல் செயல்பாடுகளை எத்தனை <strong class=\"hi-mod\">நாட்கள்</strong> செய்தீர்கள்? நடைப்பயிற்சியை சேர்க்க வேண்டாம்."
          },
          ttsPrompt: {
            en: "During the last 7 days, on how many days did you do moderate physical activities like carrying light loads, bicycling at a regular pace, or doubles tennis? Do not include walking.",
            ta: "கடந்த 7 நாட்களில், இலகுவான பொருட்களை சுமந்து செல்வது, சாதாரண வேகத்தில் சைக்கிள் ஓட்டுவது அல்லது இரட்டையர் டென்னிஸ் போன்ற மிதமான உடல் செயல்பாடுகளை எத்தனை நாட்கள் செய்தீர்கள்? நடைப்பயிற்சியை சேர்க்க வேண்டாம்."
          },
          inputType: "number",
          min: 0,
          max: 7,
          required: true,
          saveAs: "moderateDays",
          validation: [
            { type: 'min', value: 0, message: { en: 'Enter a number between 0 and 7. This asks for DAYS (0–7), not minutes. Example: if you did moderate activity on 3 days, enter 3.', ta: '0 முதல் 7 வரையிலான எண்ணை உள்ளிடவும். இது நாட்களை (0–7) கேட்கிறது, நிமிடங்களை அல்ல. எ.கா: 3 நாட்கள் மிதமான செயல்பாடு செய்தால், 3 ஐ உள்ளிடவும்.' } },
            { type: 'max', value: 7, message: { en: 'Enter a number between 0 and 7. This asks for DAYS (0–7), not minutes. Example: if you did moderate activity on 3 days, enter 3.', ta: '0 முதல் 7 வரையிலான எண்ணை உள்ளிடவும். இது நாட்களை (0–7) கேட்கிறது, நிமிடங்களை அல்ல. எ.கா: 3 நாட்கள் மிதமான செயல்பாடு செய்தால், 3 ஐ உள்ளிடவும்.' } }
          ]
        },
        {
          id: "moderate_minutes",
          moduleId: "mod_physical_activity",
          prompt: {
            en: "How many <strong class=\"hi-mod\">minutes</strong> did you usually spend doing <strong class=\"hi-mod\">moderate</strong> activities on one of those days?",
            ta: "அந்த நாட்களில் ஒரு நாளில் பொதுவாக எத்தனை <strong class=\"hi-mod\">நிமிடங்கள்</strong> <strong class=\"hi-mod\">மிதமான</strong> உடல் செயல்பாடுகளில் ஈடுபட்டீர்கள்?"
          },
          ttsPrompt: {
            en: "How many minutes did you usually spend doing moderate physical activities on one of those days?",
            ta: "அந்த நாட்களில் ஒரு நாளில் பொதுவாக எத்தனை நிமிடங்கள் மிதமான உடல் செயல்பாடுகளில் ஈடுபட்டீர்கள்?"
          },
          inputType: "number",
          min: 0,
          max: 480,
          required: true,
          saveAs: "moderateMinutes",
          validation: [
            { type: 'min', value: 0, message: { en: 'Enter a number between 0 and 480 minutes.', ta: '0 முதல் 480 நிமிடங்கள் வரையிலான எண்ணை உள்ளிடவும்.' } },
            { type: 'max', value: 480, message: { en: 'Enter a number between 0 and 480 minutes.', ta: '0 முதல் 480 நிமிடங்கள் வரையிலான எண்ணை உள்ளிடவும்.' } }
          ]
        },
        {
          id: "walking_days",
          moduleId: "mod_physical_activity",
          prompt: {
            en: "During the last 7 days, on how many <strong class=\"hi-mod\">days</strong> did you walk for at least 10 minutes at a time? This includes walking at work and at home, walking to travel from place to place, and any other walking that you might do solely for recreation, sport, exercise, or leisure.",
            ta: "கடந்த 7 நாட்களில், ஒரு முறையாவது குறைந்தபட்சம் 10 நிமிடங்கள் தொடர்ந்து நடந்த <strong class=\"hi-mod\">நாட்கள்</strong> எத்தனை? இதில் வேலையில் நடப்பது, வீட்டில் நடப்பது, ஒரு இடத்திலிருந்து மற்றொரு இடத்திற்கு நடப்பது, மற்றும் பொழுதுபோக்கு, விளையாட்டு, உடற்பயிற்சி அல்லது ஓய்வு நேரத்தில் நடப்பது ஆகியவை அடங்கும்."
          },
          ttsPrompt: {
            en: "During the last 7 days, on how many days did you walk for at least 10 minutes at a time? This includes walking at work and at home, walking to travel from place to place, and any other walking that you might do solely for recreation, sport, exercise, or leisure.",
            ta: "கடந்த 7 நாட்களில், ஒரு முறையாவது குறைந்தபட்சம் 10 நிமிடங்கள் தொடர்ந்து நடந்த நாட்கள் எத்தனை? இதில் வேலையில் நடப்பது, வீட்டில் நடப்பது, ஒரு இடத்திலிருந்து மற்றொரு இடத்திற்கு நடப்பது, மற்றும் பொழுதுபோக்கு, விளையாட்டு, உடற்பயிற்சி அல்லது ஓய்வு நேரத்தில் நடப்பது ஆகியவை அடங்கும்."
          },
          inputType: "number",
          min: 0,
          max: 7,
          required: true,
          saveAs: "walkingDays",
          validation: [
            { type: 'min', value: 0, message: { en: 'Enter a number between 0 and 7. This asks for DAYS (0–7), not minutes. Example: if you walked on 3 days, enter 3.', ta: '0 முதல் 7 வரையிலான எண்ணை உள்ளிடவும். இது நாட்களை (0–7) கேட்கிறது, நிமிடங்களை அல்ல. எ.கா: 3 நாட்கள் நடந்தால், 3 ஐ உள்ளிடவும்.' } },
            { type: 'max', value: 7, message: { en: 'Enter a number between 0 and 7. This asks for DAYS (0–7), not minutes. Example: if you walked on 3 days, enter 3.', ta: '0 முதல் 7 வரையிலான எண்ணை உள்ளிடவும். இது நாட்களை (0–7) கேட்கிறது, நிமிடங்களை அல்ல. எ.கா: 3 நாட்கள் நடந்தால், 3 ஐ உள்ளிடவும்.' } }
          ]
        },
        {
          id: "walking_minutes",
          moduleId: "mod_physical_activity",
          prompt: {
            en: "How many <strong class=\"hi-mod\">minutes</strong> did you usually spend <strong class=\"hi-mod\">walking</strong> on one of those days?",
            ta: "அந்த நாட்களில் ஒரு நாளில் பொதுவாக எத்தனை <strong class=\"hi-mod\">நிமிடங்கள்</strong> <strong class=\"hi-mod\">நடந்தீர்கள்</strong>?"
          },
          ttsPrompt: {
            en: "How many hours did you usually spend walking on one of those days? (in minutes)",
            ta: "அந்த நாட்களில் ஒரு நாளில் பொதுவாக எத்தனை மணி நேரம் நடந்தீர்கள்? (நிமிடங்களில்)"
          },
          inputType: "number",
          min: 0,
          max: 480,
          required: true,
          saveAs: "walkingMinutes",
          validation: [
            { type: 'min', value: 0, message: { en: 'Enter a number between 0 and 480 minutes.', ta: '0 முதல் 480 நிமிடங்கள் வரையிலான எண்ணை உள்ளிடவும்.' } },
            { type: 'max', value: 480, message: { en: 'Enter a number between 0 and 480 minutes.', ta: '0 முதல் 480 நிமிடங்கள் வரையிலான எண்ணை உள்ளிடவும்.' } }
          ]
        },
        {
          id: "sitting_hours",
          moduleId: "mod_physical_activity",
          prompt: {
            en: "How many hours per day do you spend sitting? Include time spent sitting at work, at home, while doing course work or reading, sitting to watch Television during leisure time.",
            ta: "ஒரு நாளைக்கு எத்தனை மணி நேரம் உட்கார்ந்து செலவிடுகிறீர்கள்? வேலையில், வீட்டில், பாடம் படிக்கும்போது அல்லது படிக்கும்போது, ஓய்வு நேரத்தில் டிவி பார்க்கும்போது உட்கார்ந்த நேரம் இதில் அடங்கும்."
          },
          inputType: "number",
          min: 0,
          max: 24,
          required: true,
          saveAs: "sittingHours",
          validation: [
            { type: 'min', value: 0, message: { en: 'Hours per day cannot be less than 0. Enter a value between 0 and 24.', ta: 'ஒரு நாளைக்கு மணி நேரம் 0 க்கும் குறைவாக இருக்க முடியாது. 0 முதல் 24 வரை உள்ளிடவும்.' } },
            { type: 'max', value: 24, message: { en: 'Hours per day cannot exceed 24. Enter a value between 0 and 24.', ta: 'ஒரு நாளைக்கு மணி நேரம் 24 ஐ தாண்ட முடியாது. 0 முதல் 24 வரை உள்ளிடவும்.' } }
          ]
        }
      ]
    },
    {
      id: "mod_parq",
      title: { en: "PAR-Q Safety", ta: "உடற்தகுதி கேள்வித்தாள் (PAR-Q)" },
      purpose: "Safety screening for cardiovascular and joint risks.",
      questions: [
        {
          id: "parq_heart",
          moduleId: "mod_parq",
          prompt: {
            en: "Has your doctor ever said that you have a heart condition and that you should only do physical activity recommended by a doctor?",
            ta: "உங்களுக்கு இதய நோய் இருப்பதாகவும், மருத்துவர் பரிந்துரைக்கும் பயிற்சிகளை மட்டுமே செய்ய வேண்டும் என்றும் எப்போதாவது மருத்துவர் கூறியிருக்கிறாரா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "parqHeartCondition"
        },
        {
          id: "parq_chest_active",
          moduleId: "mod_parq",
          prompt: {
            en: "Do you feel pain in your chest when you do physical activity?",
            ta: "உடற்பயிற்சி செய்யும் போது உங்கள் நெஞ்சில் வலி ஏற்படுகிறதா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "parqChestPainActivity"
        },
        {
          id: "parq_chest_rest",
          moduleId: "mod_parq",
          prompt: {
            en: "In the past month, have you had chest pain when you were not doing physical activity?",
            ta: "கடந்த மாதத்தில், உடற்பயிற்சி செய்யாத போதும் உங்களுக்கு நெஞ்சு வலி ஏற்பட்டதா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "parqChestPainRest"
        },
        {
          id: "parq_balance",
          moduleId: "mod_parq",
          prompt: {
            en: "Do you lose your balance because of dizziness or do you ever lose consciousness?",
            ta: "தலைச்சுற்றல் காரணமாக நீங்கள் சமநிலையை இழக்கிறீர்களா அல்லது மயக்கம் அடைந்தது உண்டா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "parqDizziness"
        },
        {
          id: "parq_bone",
          moduleId: "mod_parq",
          prompt: {
            en: "Do you have a bone or joint problem that could be made worse by a change in your physical activity?",
            ta: "உடல் செயல்பாடுகளை மாற்றுவதால் மோசமடையக்கூடிய எலும்பு அல்லது மூட்டு பிரச்சனைகள் ஏதேனும் உங்களுக்கு உள்ளதா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "parqBoneJoint"
        },
        {
          id: "parq_drugs",
          moduleId: "mod_parq",
          prompt: {
            en: "Is your doctor currently prescribing drugs (for example, water pills) for your blood pressure or heart condition?",
            ta: "உயர் இரத்த அழுத்தம் அல்லது இதய நோய்க்காக தற்போது ஏதேனும் மருந்துகளை மருத்துவர் பரிந்துரைக்கிறாரா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "parqDrugs"
        },
        {
          id: "parq_other",
          moduleId: "mod_parq",
          prompt: {
            en: "Do you know of any other reason why you should not do physical activity?",
            ta: "நீங்கள் உடற்பயிற்சி செய்யக்கூடாது என்பதற்கு வேறு ஏதேனும் காரணம் உங்களுக்குத் தெரியுமா?"
          },
          inputType: "single_choice",
          options: [
            { value: "yes", label: { en: "Yes", ta: "ஆம்" } },
            { value: "no", label: { en: "No", ta: "இல்லை" } }
          ],
          required: true,
          saveAs: "parqOtherReason"
        }
      ]
    },
    {
      id: "mod_motivation",
      title: { en: "Goals & Motivation", ta: "இலக்குகள் & ஊக்கம்" },
      purpose: "Identify enjoyment, confidence level, preferred activities, and structural barriers.",
      questions: [
        {
          id: "confidence",
          moduleId: "mod_motivation",
          prompt: {
            en: "How confident are you about exercising regularly (on a scale of 1 to 5)?",
            ta: "தொடர்ந்து உடற்பயிற்சி செய்வது பற்றி உங்களுக்கு எவ்வளவு நம்பிக்கை உள்ளது (1 முதல் 5 வரையிலான அளவில்)?"
          },
          inputType: "scale",
          min: 1,
          max: 5,
          required: true,
          saveAs: "confidenceLevel"
        },
        {
          id: "exercise_types",
          moduleId: "mod_motivation",
          prompt: {
            en: "What type of exercise do you enjoy the most? (You can select multiple)",
            ta: "நீங்கள் மிகவும் விரும்பும் உடற்பயிற்சி வகை எது? (நீங்கள் பலவற்றைத் தேர்ந்தெடுக்கலாம்)"
          },
          inputType: "multi_choice",
          options: [
            { value: "walking", label: { en: "Walking", ta: "நடைப்பயிற்சி" } },
            { value: "cycling", label: { en: "Cycling", ta: "சைக்கிள் ஓட்டுதல்" } },
            { value: "yoga", label: { en: "Yoga / Stretching", ta: "யோகா / நீட்சி" } },
            { value: "swimming", label: { en: "Swimming", ta: "நீச்சல்" } },
            { value: "sports", label: { en: "Sports (Badminton, etc.)", ta: "விளையாட்டு (பேட்மிண்டன் போன்றவை)" } }
          ],
          required: true,
          saveAs: "preferredExerciseTypes"
        },
        {
          id: "enjoyment",
          moduleId: "mod_motivation",
          prompt: {
            en: "On a scale of 1-10, how much do you enjoy physical activity generally?",
            ta: "பொதுவாக உடற்பயிற்சியை நீங்கள் எவ்வளவு ரசிக்கிறீர்கள் (1-10 அளவில்)?"
          },
          inputType: "scale",
          min: 1,
          max: 10,
          required: true,
          saveAs: "enjoymentScore"
        },
        {
          id: "barriers",
          moduleId: "mod_motivation",
          prompt: {
            en: "What prevents you from exercising regularly? (You can select multiple)",
            ta: "தொடர்ந்து உடற்பயிற்சி செய்வதைத் தடுப்பது எது? (நீங்கள் பலவற்றைத் தேர்ந்தெடுக்கலாம்)"
          },
          inputType: "multi_choice",
          options: [
            { value: "time", label: { en: "Lack of time", ta: "நேரமின்மை" } },
            { value: "pain", label: { en: "Joint pain or discomfort", ta: "மூட்டு வலி அல்லது அசௌகரியம்" } },
            { value: "fatigue", label: { en: "Severe fatigue or low energy", ta: "அதிக சோர்வு அல்லது குறைந்த ஆற்றல்" } },
            { value: "hypo_fear", label: { en: "Fear of low blood sugar", ta: "சர்க்கரை அளவு குறைந்துவிடுமோ என்ற பயம்" } },
            { value: "no_space", label: { en: "No safe space to walk/exercise", ta: "உடற்பயிற்சி செய்ய பாதுகாப்பான இடம் இல்லை" } },
            { value: "motivation", label: { en: "Lack of motivation", ta: "ஊக்கமின்மை" } }
          ],
          required: true,
          saveAs: "exerciseBarriers"
        }
      ]
    },
    {
      id: "mod_lifestyle",
      title: { en: "Other Lifestyle Domains", ta: "வாழ்க்கை முறை காரணிகள்" },
      purpose: "Assess sleep patterns, perceived stress, and diet behaviors.",
      questions: [
        {
          id: "sleep_hours",
          moduleId: "mod_lifestyle",
          prompt: {
            en: "How many hours of sleep do you usually get each night?",
            ta: "பொதுவாக ஒரு இரவில் நீங்கள் எத்தனை மணி நேரம் தூங்குகிறீர்கள்?"
          },
          inputType: "number",
          min: 2,
          max: 16,
          required: true,
          saveAs: "sleepHours"
        },
        {
          id: "stress",
          moduleId: "mod_lifestyle",
          prompt: {
            en: "How stressed do you feel on a typical day?",
            ta: "ஒரு சாதாரண நாளில் நீங்கள் எவ்வளவு மன அழுத்தத்தை உணர்கிறீர்கள்?"
          },
          inputType: "single_choice",
          options: [
            { value: "low", label: { en: "Low", ta: "குறைவு" } },
            { value: "moderate", label: { en: "Moderate", ta: "மிதமானது" } },
            { value: "high", label: { en: "High", ta: "அதிகம்" } }
          ],
          required: true,
          saveAs: "stressLevel"
        },
        {
          id: "junk_food",
          moduleId: "mod_lifestyle",
          prompt: {
            en: "How often do you consume junk food or sugary drinks per week?",
            ta: "வாரத்திற்கு எத்தனை முறை நீங்கள் துரித உணவுகள் (ஜங்க் புட்) அல்லது இனிப்பு பானங்களை உட்கொள்கிறீர்கள்?"
          },
          inputType: "single_choice",
          options: [
            { value: "never", label: { en: "Never / Rarely", ta: "ஒருபோதும் இல்லை / அரிதாக" } },
            { value: "sometimes", label: { en: "1-2 times a week", ta: "வாரத்திற்கு 1-2 முறை" } },
            { value: "frequent", label: { en: "3 or more times a week", ta: "வாரத்திற்கு 3 முறை அல்லது அதற்கு மேல்" } }
          ],
          required: true,
          saveAs: "junkFoodFrequency"
        }
      ]
    },
    {
      id: "mod_prescription",
      title: { en: "Prescription", ta: "பரிந்துரைப்பு" },
      purpose: "Prompt to show custom plan.",
      questions: [
        {
          id: "view_prescription",
          moduleId: "mod_prescription",
          prompt: {
            en: "Based on all your responses, I have prepared your personalized DiaFit physical activity plan. Are you ready to view it?",
            ta: "உங்கள் பதில்களின் அடிப்படையில், உங்களுக்கான தனிப்பயனாக்கப்பட்ட டயாஃபிட் உடற்பயிற்சி திட்டத்தை நான் தயாரித்துள்ளேன். அதை நீங்கள் பார்க்க தயாரா?"
          },
          inputType: "confirmation",
          options: [
            { value: "yes", label: { en: "Yes, show my plan", ta: "ஆம், எனது திட்டத்தைக் காட்டு" } }
          ],
          required: true,
          saveAs: "wantsPrescription"
        }
      ]
    }
  ]
};
