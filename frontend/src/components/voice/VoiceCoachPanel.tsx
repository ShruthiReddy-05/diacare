import { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useVoiceCoachStore } from '../../stores/useVoiceCoachStore';
import { useAssessmentStore } from '../../stores/useAssessmentStore';
import { useUserStore } from '../../stores/useUserStore';
import { translations } from '../../data/translations';
import { initialAssessmentQuestionnaire } from '../../data/questionnaires/initialAssessment';
import { useSpeech } from '../../services/speech/SpeechContext';
import VoiceFlowIndicator from './VoiceFlowIndicator';
import { Mic, Headphones, X, Check, RotateCcw } from 'lucide-react';

interface Props {
  onVoiceAnswer?: (transcript: string) => void;
}

export default function VoiceCoachPanel({ onVoiceAnswer }: Props) {
  const { flowState, isEnabled, transcript, displayText, disable, setFlowState } = useVoiceCoachStore();
  const { currentQuestionId } = useAssessmentStore();
  const { language } = useUserStore();
  const t = translations[language];
  const { startListening, stopListening, stop } = useSpeech();

  const currentQuestion = useMemo(() => {
    if (!currentQuestionId) return null;
    const allQ = initialAssessmentQuestionnaire.modules.flatMap(m => m.questions);
    return allQ.find(q => q.id === currentQuestionId) || null;
  }, [currentQuestionId]);

  if (!isEnabled) return null;

  const handleStartVoice = async () => {
    setFlowState('listening');
    await startListening(language, currentQuestion?.inputType);
  };

  const handleConfirmTranscript = () => {
    stopListening();
    onVoiceAnswer?.(transcript);
    setFlowState('validating_answer');
  };

  const handleRetry = async () => {
    stopListening();
    setFlowState('listening');
    await startListening(language, currentQuestion?.inputType);
  };

  const handleStop = () => {
    stop();
    stopListening();
    disable();
  };

  return (
    <AnimatePresence>
      {isEnabled && (
        <motion.div
          className="voice-coach-panel"
          initial={{ y: 80, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 80, opacity: 0 }}
        >
          <div className="voice-panel-header">
            <Headphones size={18} />
            <span className="voice-panel-title">{t.voiceCoachMode}</span>
            <button className="voice-close-btn" onClick={handleStop}>
              <X size={18} />
            </button>
          </div>

          <VoiceFlowIndicator />

          {(flowState === 'listening' || flowState === 'confirming_transcript') && (
            <div className="voice-transcript-area">
              {flowState === 'listening' ? (
                <motion.button
                  className="voice-mic-btn"
                  whileTap={{ scale: 0.9 }}
                  onClick={handleStartVoice}
                >
                  <Mic size={32} />
                </motion.button>
              ) : (
                <div className="voice-confirm">
                  <p className="confirm-label">{t.transcriptConfirm}</p>
                  <p className="confirm-text">{displayText}</p>
                  <div className="confirm-actions">
                    <button className="voice-confirm-btn" onClick={handleConfirmTranscript}>
                      <Check size={18} /> {t.confirmSpeech}
                    </button>
                    <button className="voice-retry-btn" onClick={handleRetry}>
                      <RotateCcw size={18} /> {t.retrySpeech}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {(flowState === 'speaking_question' || flowState === 'paused') && (
            <div className="voice-status-text">
              {flowState === 'speaking_question' ? t.voiceDesc : t.pauseVoice}
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
