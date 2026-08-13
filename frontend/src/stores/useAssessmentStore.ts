import { create } from 'zustand';
import type { AssessmentState, RiskResult, AiExercisePrescription } from '../domain/types';
import { initialAssessmentQuestionnaire } from '../data/questionnaires/initialAssessment';
import { getNextQuestion } from '../domain/questionnaireEngine';
import { calculateRisk, selectPlanType } from '../domain/riskEngine';
import { api } from '../services/api/client';

function stripHtml(text: string): string {
  return text.replace(/<[^>]*>/g, '');
}

interface AssessmentStore {
  sessionId: string | null;
  currentQuestionId: string | null;
  answers: Record<string, any>;
  riskResult: RiskResult | null;
  prescription: AiExercisePrescription | null;
  isComplete: boolean;
  isSubmitting: boolean;
  error: string | null;
  _startingSession: boolean;

  startAssessment: (userId: string) => Promise<void>;
  submitAnswer: (questionId: string, value: any, userId: string, language: string) => Promise<void>;
  completeAssessment: (userId: string, language: string) => Promise<void>;
  setAnswer: (key: string, value: any) => void;
  reset: () => void;
  loadAnswers: (sessionId: string) => Promise<void>;
}

export const useAssessmentStore = create<AssessmentStore>((set, get) => ({
  sessionId: null,
  currentQuestionId: null,
  answers: {},
  riskResult: null,
  prescription: null,
  isComplete: false,
  isSubmitting: false,
  error: null,
  _startingSession: false,

  startAssessment: async (userId) => {
    const state = get();
    if (state._startingSession) return;
    set({ _startingSession: true, isSubmitting: true, error: null });
    try {
      const q = initialAssessmentQuestionnaire;
      const session = await api.createAssessmentSession(userId, {
        questionnaire_id: q.id,
        questionnaire_version: q.version,
      });
      const firstQ = getNextQuestion(null, {}, q);
      set({
        sessionId: session.id,
        currentQuestionId: firstQ?.id || null,
        answers: {},
        riskResult: null,
        prescription: null,
        isComplete: false,
        isSubmitting: false,
        _startingSession: false,
      });
    } catch (e: any) {
      set({ isSubmitting: false, error: e.message, _startingSession: false });
    }
  },

  submitAnswer: async (questionId, value, _userId, language) => {
    const state = get();
    const { sessionId, answers } = state;
    if (!sessionId) return;

    const q = initialAssessmentQuestionnaire;
    const allQuestions = q.modules.flatMap(m => m.questions);
    const question = allQuestions.find(qq => qq.id === questionId);
    const saveAs = question?.saveAs || questionId;

    let newAnswers: Record<string, any>;
    if (questionId === 'height_weight') {
      newAnswers = { ...answers, heightCm: value.heightCm, weightKg: value.weightKg };
    } else {
      newAnswers = { ...answers, [saveAs]: value };
    }

    set({ answers: newAnswers, isSubmitting: true });

    try {
      let answerStr: string;
      if (questionId === 'height_weight' && typeof value === 'object' && value !== null) {
        answerStr = `${value.heightCm}cm,${value.weightKg}kg`;
      } else {
        answerStr = String(value);
      }

      await api.submitResponse(sessionId, {
        question_id: questionId,
        module_id: question?.moduleId || '',
        question_text_en: stripHtml(question?.prompt.en || ''),
        question_text_ta: stripHtml(question?.prompt.ta || ''),
        answer_value: answerStr,
        answer_display_label: question?.options?.find(o => o.value === value)?.label || null,
        language,
      });

      const nextQ = getNextQuestion(questionId, newAnswers, q);
      set({ currentQuestionId: nextQ?.id || null, isSubmitting: false });
    } catch (e: any) {
      set({ isSubmitting: false, error: e.message });
    }
  },

  completeAssessment: async (_userId, language) => {
    const { sessionId, answers, riskResult } = get();
    if (!sessionId) return;

    set({ isSubmitting: true, error: null });

    try {
      const assessmentState: AssessmentState = { language: language as any, ...answers };
      const risk = riskResult || calculateRisk(assessmentState);
      await api.completeAssessment(sessionId);

      let prescription: AiExercisePrescription | null = null;
      try {
        const planType = selectPlanType(risk, assessmentState);
        const presData = await api.generatePrescription(sessionId, language);
        if (presData?.prescription_snapshot) {
          prescription = presData.prescription_snapshot;
        } else {
          prescription = {
            planType,
            userSummary: '',
            activityPlan: [],
            simpleActivities: [],
            strengthExercises: [],
            personalizedTips: [],
            safetyWarnings: [],
            medicalClearanceRequired: planType === 'medical_clearance_required',
            ragSourceIds: [],
          };
        }
      } catch {
        // Prescription generation may fail without Together AI key — still complete
      }

      set({ isComplete: true, riskResult: risk, prescription, isSubmitting: false });
    } catch (e: any) {
      set({ isSubmitting: false, error: e.message });
    }
  },

  setAnswer: (key, value) => {
    const { answers } = get();
    set({ answers: { ...answers, [key]: value } });
  },

  reset: () => set({
    sessionId: null,
    currentQuestionId: null,
    answers: {},
    riskResult: null,
    prescription: null,
    isComplete: false,
    isSubmitting: false,
    error: null,
    _startingSession: false,
  }),

  loadAnswers: async (sessionId) => {
    try {
      const session = await api.getAssessmentSession(sessionId);
      if (session?.responses) {
        const ans: Record<string, any> = {};
        for (const r of session.responses) {
          ans[r.question_id] = r.answer_value;
        }
        set({ answers: ans });
      }
    } catch {
      // silent
    }
  },
}));
