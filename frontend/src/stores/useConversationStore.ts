import { create } from 'zustand';
import type { ConversationScript } from '../domain/types';
import { parseScript, getNextQuestionInSitting } from '../domain/conversationEngine';
import { api } from '../services/api/client';

function stripHtml(text: string): string {
  return text.replace(/<[^>]*>/g, '');
}

interface ConversationStore {
  script: ConversationScript | null;
  sessionId: string | null;
  sitting: string | null;
  currentQuestionId: string | null;
  answers: Record<string, any>;
  responses: any[];
  isSittingComplete: boolean;
  isSubmitting: boolean;
  error: string | null;
  _startingSession: boolean;

  loadScript: () => Promise<ConversationScript>;
  startSitting: (userId: string, sitting: string, preferredCheckinTime?: string) => Promise<void>;
  submitAnswer: (questionId: string, moduleId: string, value: any, language: string, inputModality?: 'speech' | 'touch') => Promise<void>;
  completeSitting: () => Promise<void>;
  reset: () => void;
}

export const useConversationStore = create<ConversationStore>((set, get) => ({
  script: null,
  sessionId: null,
  sitting: null,
  currentQuestionId: null,
  answers: {},
  responses: [],
  isSittingComplete: false,
  isSubmitting: false,
  error: null,
  _startingSession: false,

  loadScript: async () => {
    const existing = get().script;
    if (existing) return existing;
    const raw = await api.getScript();
    const script = parseScript(raw);
    set({ script });
    return script;
  },

  startSitting: async (userId, sitting, preferredCheckinTime) => {
    const state = get();
    if (state._startingSession) return;
    set({ _startingSession: true, isSubmitting: true, error: null, isSittingComplete: false });
    try {
      const script = await get().loadScript();
      const session = await api.createConversationSession(userId, {
        script_id: script.id,
        script_version: script.version,
        sitting,
        preferred_checkin_time: preferredCheckinTime,
      });

      const responses: any[] = session.responses || [];
      const answeredIds = new Set(responses.map((r: any) => r.question_id));
      const sittingQuestions = script.modules.filter(m => m.sitting === sitting).flatMap(m => m.questions);
      const nextQ = sittingQuestions.find(q => !answeredIds.has(q.id)) || null;

      set({
        sessionId: session.id,
        sitting,
        currentQuestionId: nextQ?.id || null,
        answers: {},
        responses,
        isSittingComplete: !nextQ && sittingQuestions.length > 0,
        isSubmitting: false,
        _startingSession: false,
      });
    } catch (e: any) {
      set({ isSubmitting: false, error: e.message, _startingSession: false });
    }
  },

  submitAnswer: async (questionId, moduleId, value, language, inputModality = 'touch') => {
    const state = get();
    const { sessionId, sitting, script, answers } = state;
    if (!sessionId || !sitting || !script) return;

    const allQuestions = script.modules.flatMap(m => m.questions);
    const question = allQuestions.find(q => q.id === questionId);
    const saveAs = question?.saveAs || questionId;

    const newAnswers = { ...answers, [saveAs]: value };
    set({ answers: newAnswers, isSubmitting: true });

    try {
      let answerStr: string;
      if (questionId === 'height_weight' && typeof value === 'object' && value !== null) {
        answerStr = `${value.heightCm},${value.weightKg}`;
      } else if (typeof value === 'object' && value !== null) {
        answerStr = JSON.stringify(value);
      } else {
        answerStr = String(value);
      }

      const displayLabel = question?.options?.find(o => o.value === value)?.label || null;

      await api.submitConversationResponse(sessionId, {
        module_id: moduleId,
        question_id: questionId,
        question_text_en: stripHtml(question?.prompt.en || ''),
        question_text_ta: stripHtml(question?.prompt.ta || ''),
        answer_value: answerStr,
        answer_display_label: displayLabel,
        language,
        input_modality: inputModality,
      });

      const nextQ = getNextQuestionInSitting(questionId, sitting, script);
      set({ currentQuestionId: nextQ?.id || null, isSittingComplete: !nextQ, isSubmitting: false });
    } catch (e: any) {
      set({ isSubmitting: false, error: e.message });
    }
  },

  completeSitting: async () => {
    const { sessionId, sitting } = get();
    if (!sessionId || !sitting) return;
    set({ isSubmitting: true, error: null });
    try {
      await api.completeSitting(sessionId, sitting);
      set({ isSittingComplete: true, isSubmitting: false });
    } catch (e: any) {
      set({ isSubmitting: false, error: e.message });
    }
  },

  reset: () => set({
    sessionId: null,
    sitting: null,
    currentQuestionId: null,
    answers: {},
    responses: [],
    isSittingComplete: false,
    isSubmitting: false,
    error: null,
    _startingSession: false,
  }),
}));
