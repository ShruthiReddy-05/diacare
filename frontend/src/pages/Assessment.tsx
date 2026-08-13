import { matchVoiceTranscript } from '../utils/voiceTranscriptMatcher';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useUserStore } from '../stores/useUserStore';
import { useAssessmentStore } from '../stores/useAssessmentStore';
import { useVoiceCoachStore } from '../stores/useVoiceCoachStore';
import { useSpeech } from '../services/speech/SpeechContext';
import { translations } from '../data/translations';
import { initialAssessmentQuestionnaire } from '../data/questionnaires/initialAssessment';
import { validateAnswer, getAllQuestionIds } from '../domain/questionnaireEngine';
import ChatWindow from '../components/assessment/ChatWindow';
import QuestionInput from '../components/assessment/QuestionInput';
import ProgressBar from '../components/assessment/ProgressBar';
import VoiceDock from '../components/voice/VoiceDock';
import VoiceCoachPanel from '../components/voice/VoiceCoachPanel';
import AppBar from '../components/common/AppBar';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function Assessment() {
  const navigate = useNavigate();
  const { language, user } = useUserStore();
  const {
    sessionId, currentQuestionId, answers, isComplete,
    error, startAssessment, submitAnswer,
    completeAssessment, reset
  } = useAssessmentStore();
  const { setFlowState, isEnabled } = useVoiceCoachStore();
  const { speak, stop, startListening } = useSpeech();
  const t = translations[language];
  const submittingRef = useRef(false);

  const [messages, setMessages] = useState<{ id: string; role: 'bot' | 'user'; text: string }[]>([]);
  const [inputValue, setInputValue] = useState<any>(undefined);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const q = initialAssessmentQuestionnaire;
  const allQuestions = q.modules.flatMap(m => m.questions);
  const allQuestionIds = getAllQuestionIds(q);
  const totalQuestions = allQuestionIds.length;
  const answeredCount = allQuestionIds.filter(id => {
    const question = allQuestions.find(qq => qq.id === id);
    if (!question) return false;
    const val = answers[question.saveAs];
    return val !== undefined && val !== null && val !== '';
  }).length;

  const currentQ = currentQuestionId ? allQuestions.find(qq => qq.id === currentQuestionId) || null : null;
  const currentModuleId = currentQ?.moduleId || null;

  useEffect(() => {
    if (!user) {
      navigate('/');
    }
  }, [user]);

  useEffect(() => {
    return () => { reset(); };
  }, []);

  useEffect(() => {
    if (isComplete) {
      navigate('/prescription/latest');
    }
  }, [isComplete]);

  const handleStart = async () => {
    if (!user || starting) return;
    setStarting(true);
    try {
      await startAssessment(user.id);
      if (!useAssessmentStore.getState().sessionId) {
        console.error('startAssessment completed but sessionId is still null');
      }
    } catch (e) {
      console.error('startAssessment failed', e);
    } finally {
      setStarting(false);
    }
  };

  useEffect(() => {
    if (isEnabled && currentQ) {
      const text = currentQ.ttsPrompt?.[language] || currentQ.prompt[language];
      setFlowState('speaking_question');
      speak(text, language, currentQ.id, initialAssessmentQuestionnaire.id).then(async () => {
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

  const handleSubmit = useCallback(async (overrideValue?: any) => {
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

    setMessages(prev => [...prev, {
      id: `user-${Date.now()}`,
      role: 'user',
      text: answerText,
    }]);

    setInputValue(undefined);

    try {
      await submitAnswer(currentQ.id, answerValue, user.id, language);
    } finally {
      submittingRef.current = false;
    }

    if (currentQ.id === 'shall_we_begin' && answerValue === 'no') {
      navigate('/home');
    }
  }, [currentQ, inputValue, user, sessionId, language]);

  const handleComplete = useCallback(async () => {
    if (!user || submittingRef.current) return;
    stop();
    submittingRef.current = true;
    try {
      await completeAssessment(user.id, language);
    } finally {
      submittingRef.current = false;
    }
  }, [user, language]);

  const handleRepeat = () => {
    if (currentQ) {
      stop();
      const text = currentQ.ttsPrompt?.[language] || currentQ.prompt[language];
      setFlowState('speaking_question');
      speak(text, language, currentQ.id, initialAssessmentQuestionnaire.id).then(() => {
        setFlowState('listening');
        startListening(language, currentQ.inputType);
      });
    }
  };

  const handleVoiceAnswer = useCallback((transcript: string) => {
    if (submittingRef.current || !currentQ) return;
    const parsed = matchVoiceTranscript(transcript, currentQ, language);
    if (currentQ.inputType === 'confirmation') {
      handleComplete();
    } else {
      handleSubmit(parsed);
    }
  }, [handleSubmit, handleComplete, currentQ, language]);

  if (!sessionId) {
    return (
      <div className="page-container">
        <AppBar title={t.assessment} showBack onBack={() => navigate('/home')} />
        <main className="page-content" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20, textAlign: 'center', paddingTop: 60 }}>
          <h2 style={{ fontSize: 22 }}>Health Assessment</h2>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, maxWidth: 320 }}>
            This will help us understand your health profile and create a personalized exercise plan for you.
          </p>
          <button className="btn-primary" onClick={handleStart} disabled={starting} style={{ marginTop: 16 }}>
            {starting ? 'Starting...' : 'Start Assessment'}
          </button>
        </main>
      </div>
    );
  }

  if (!currentQ) {
    return (
      <div className="page-container">
        <AppBar title={t.assessment} showBack onBack={() => navigate('/home')} />
        <main className="page-content">
          <LoadingSpinner text="Starting assessment..." />
        </main>
      </div>
    );
  }

  return (
    <div className="page-container assessment-page">
      <AppBar
        title={t.assessment}
        showBack
        onBack={() => navigate('/home')}
      />

      <ProgressBar
        answered={answeredCount}
        total={totalQuestions}
        moduleTitle={q.modules.find(m => m.id === currentModuleId)?.title?.[language]}
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
              onSubmit={
                currentQ.inputType === 'confirmation' ? handleComplete : handleSubmit
              }
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
