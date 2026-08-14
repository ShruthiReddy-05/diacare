import { matchVoiceTranscript } from '../utils/voiceTranscriptMatcher';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useUserStore } from '../stores/useUserStore';
import { useConversationStore } from '../stores/useConversationStore';
import { useVoiceCoachStore } from '../stores/useVoiceCoachStore';
import { useSpeech } from '../services/speech/SpeechContext';
import { translations } from '../data/translations';
import { validateAnswer } from '../domain/conversationEngine';
import api from '../services/api/client';
import ChatWindow from '../components/assessment/ChatWindow';
import QuestionInput from '../components/assessment/QuestionInput';
import ProgressBar from '../components/assessment/ProgressBar';
import VoiceDock from '../components/voice/VoiceDock';
import VoiceCoachPanel from '../components/voice/VoiceCoachPanel';
import AppBar from '../components/common/AppBar';
import LoadingSpinner from '../components/common/LoadingSpinner';

function stripHtml(text: string): string {
  return text.replace(/<[^>]*>/g, '');
}

const SITTING_TITLES: Record<string, { en: string; ta: string }> = {
  '1': { en: 'Getting to Know You', ta: 'உங்களை அறிந்துகொள்ளுதல்' },
  '2': { en: 'Food & Activity', ta: 'உணவு மற்றும் செயல்பாடு' },
  '3': { en: 'Medicines & Coping', ta: 'மருந்துகள் மற்றும் சமாளிப்பு' },
};

export default function Conversation() {
  const { sitting: sittingParam } = useParams();
  const sitting = sittingParam || '1';
  const navigate = useNavigate();
  const { language, user } = useUserStore();
  const {
    script, sessionId, currentQuestionId, isSittingComplete,
    error, loadScript, startSitting, submitAnswer, completeSitting, reset,
  } = useConversationStore();
  const { setFlowState, isEnabled } = useVoiceCoachStore();
  const { speak, stop, startListening } = useSpeech();
  const t = translations[language];
  const submittingRef = useRef(false);
  const finishingRef = useRef(false);

  const [messages, setMessages] = useState<{ id: string; role: 'bot' | 'user'; text: string }[]>([]);
  const [inputValue, setInputValue] = useState<any>(undefined);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [answeredIds, setAnsweredIds] = useState<Set<string>>(new Set());

  const sittingQuestions = script ? script.modules.filter(m => m.sitting === sitting).flatMap(m => m.questions) : [];
  const totalQuestions = sittingQuestions.length;
  const answeredCount = answeredIds.size;
  const currentQ = currentQuestionId ? sittingQuestions.find(q => q.id === currentQuestionId) || null : null;
  const currentModuleId = currentQ?.moduleId || null;
  const currentModuleTitle = script?.modules.find(m => m.id === currentModuleId)?.title?.[language];

  useEffect(() => {
    if (!user) { navigate('/'); return; }
    loadScript().catch(() => {});
  }, [user]);

  useEffect(() => {
    return () => { reset(); };
  }, [sitting]);

  useEffect(() => {
    if (!isSittingComplete || !sessionId || finishingRef.current || !user) return;
    finishingRef.current = true;
    (async () => {
      await completeSitting();
      if (sitting === '3') {
        try { await api.generateCarePlan(user.id); } catch { /* still navigate */ }
        navigate('/care-plan/latest');
      } else {
        navigate('/home');
      }
    })();
  }, [isSittingComplete, sessionId, sitting, user]);

  const handleStart = async () => {
    if (!user || starting) return;
    setStarting(true);
    try {
      await startSitting(user.id, sitting);
      const priorResponses: any[] = useConversationStore.getState().responses || [];
      const currentScript = useConversationStore.getState().script;
      const allQuestions = currentScript ? currentScript.modules.flatMap(m => m.questions) : [];
      setMessages(
        priorResponses.flatMap((r: any) => {
          const questionText = language === 'ta' ? r.question_text_ta : r.question_text_en;
          const fallback = allQuestions.find(q => q.id === r.question_id)?.prompt[language];
          return [
            { id: `resume-bot-${r.id}`, role: 'bot' as const, text: stripHtml(questionText || fallback || '') },
            { id: `resume-${r.id}`, role: 'user' as const, text: (r.answer_display_label?.[language]) || r.answer_value },
          ];
        })
      );
      setAnsweredIds(new Set(priorResponses.map((r: any) => r.question_id)));
    } catch (e) {
      console.error('startSitting failed', e);
    } finally {
      setStarting(false);
    }
  };

  useEffect(() => {
    if (isEnabled && currentQ && script) {
      const text = currentQ.prompt[language];
      setFlowState('speaking_question');
      speak(text, language, currentQ.id, script.id).then(async () => {
        await new Promise(r => setTimeout(r, 500));
        setFlowState('listening');
        startListening(language);
      }).catch(async () => {
        await new Promise(r => setTimeout(r, 500));
        setFlowState('listening');
        startListening(language);
      });
    }
  }, [currentQ?.id, isEnabled]);

  const handleSubmit = useCallback(async (overrideValue?: any, inputModality: 'speech' | 'touch' = 'touch') => {
    if (!currentQ || !user || !sessionId || submittingRef.current) return;
    stop();
    useVoiceCoachStore.getState().reset();
    submittingRef.current = true;

    const answerValue = overrideValue !== undefined ? overrideValue : inputValue;

    const err = validateAnswer(currentQ, answerValue);
    if (err) {
      setValidationError(err);
      submittingRef.current = false;
      return;
    }
    setValidationError(null);

    let answerText: string;
    if (typeof answerValue === 'object' && answerValue !== null && !Array.isArray(answerValue)) {
      answerText = `Height: ${answerValue.heightCm}cm, Weight: ${answerValue.weightKg}kg`;
    } else {
      const displayLabel = currentQ.options?.find(o => o.value === answerValue)?.label;
      answerText = displayLabel ? displayLabel[language] : (
        Array.isArray(answerValue) ? answerValue.join(', ') : String(answerValue ?? '')
      );
    }

    setMessages(prev => [...prev,
      { id: `bot-${currentQ.id}`, role: 'bot', text: stripHtml(currentQ.prompt[language]) },
      { id: `user-${Date.now()}`, role: 'user', text: answerText },
    ]);

    setInputValue(undefined);
    setAnsweredIds(prev => new Set(prev).add(currentQ.id));

    try {
      await submitAnswer(currentQ.id, currentQ.moduleId, answerValue, language, inputModality);
    } finally {
      submittingRef.current = false;
    }
  }, [currentQ, inputValue, user, sessionId, language]);

  const handleRepeat = () => {
    if (currentQ && script) {
      stop();
      const text = currentQ.prompt[language];
      setFlowState('speaking_question');
      speak(text, language, currentQ.id, script.id).then(() => {
        setFlowState('listening');
        startListening(language, currentQ.inputType);
      });
    }
  };

  const handleVoiceAnswer = useCallback((transcript: string) => {
    if (submittingRef.current || !currentQ) return;
    const parsed = matchVoiceTranscript(transcript, currentQ, language);
    handleSubmit(parsed, 'speech');
  }, [handleSubmit, currentQ, language]);

  const sittingTitle = SITTING_TITLES[sitting]?.[language] || t.assessment;

  if (!sessionId) {
    return (
      <div className="page-container">
        <AppBar title={sittingTitle} showBack onBack={() => navigate('/home')} />
        <main className="page-content" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20, textAlign: 'center', paddingTop: 60 }}>
          <h2 style={{ fontSize: 22 }}>{sittingTitle}</h2>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, maxWidth: 320 }}>
            {t.descAssessment}
          </p>
          <button className="btn-primary" onClick={handleStart} disabled={starting} style={{ marginTop: 16 }}>
            {starting ? '...' : t.startAssessment}
          </button>
        </main>
      </div>
    );
  }

  if (!currentQ) {
    return (
      <div className="page-container">
        <AppBar title={sittingTitle} showBack onBack={() => navigate('/home')} />
        <main className="page-content">
          <LoadingSpinner text="..." />
        </main>
      </div>
    );
  }

  return (
    <div className="page-container assessment-page">
      <AppBar
        title={sittingTitle}
        showBack
        onBack={() => navigate('/home')}
      />

      <ProgressBar
        answered={answeredCount}
        total={totalQuestions}
        moduleTitle={currentModuleTitle}
      />

      <main className="assessment-chat-area">
        <ChatWindow
          messages={messages}
          currentQuestion={currentQ}
          language={language}
        />
      </main>

      <VoiceCoachPanel onVoiceAnswer={handleVoiceAnswer} />

      <div className="assessment-input-area">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentQ.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <QuestionInput
              question={currentQ}
              value={
                currentQ.inputType === 'multi_choice' ? undefined : inputValue
              }
              onChange={(val) => { setInputValue(val); setValidationError(null); }}
              language={language}
              selectedValues={currentQ.inputType === 'multi_choice' ? (inputValue || []) : undefined}
              onSubmit={handleSubmit}
            />
          </motion.div>
        </AnimatePresence>

        {validationError && (
          <p className="validation-error">{validationError}</p>
        )}

        {error && (
          <p className="form-error">{error}</p>
        )}

        <VoiceDock onRepeat={handleRepeat} />
      </div>
    </div>
  );
}
