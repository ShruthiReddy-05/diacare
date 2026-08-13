import { useState } from 'react';
import { motion } from 'framer-motion';
import { useVoiceCoachStore } from '../../stores/useVoiceCoachStore';
import { useUserStore } from '../../stores/useUserStore';
import { translations } from '../../data/translations';
import { useSpeech } from '../../services/speech/SpeechContext';
import { MicOff, Volume2, Repeat, Pause, Play, Square } from 'lucide-react';
import VoicePrivacyConsent from './VoicePrivacyConsent';

export default function VoiceDock({ onRepeat }: { onRepeat?: () => void }) {
  const [showConsent, setShowConsent] = useState(false);
  const { isEnabled, toggleEnabled, enable } = useVoiceCoachStore();
  const { language, voiceConsentGiven, setVoiceConsent } = useUserStore();
  const t = translations[language];
  const { pause, resume, stop, isSpeaking, isPaused } = useSpeech();

  const handleToggle = () => {
    if (!isEnabled && !voiceConsentGiven) {
      setShowConsent(true);
      return;
    }
    toggleEnabled();
  };

  const handleConsentAllow = () => {
    setVoiceConsent(true);
    setShowConsent(false);
    enable();
  };

  const handleConsentDeny = () => {
    setVoiceConsent(false);
    setShowConsent(false);
  };

  return (
    <>
      {!isEnabled ? (
        <motion.button
          className="voice-dock-toggle"
          whileTap={{ scale: 0.95 }}
          onClick={handleToggle}
        >
          <MicOff size={20} />
          <span>{t.enableVoiceCoach}</span>
        </motion.button>
      ) : (
        <motion.div
          className="voice-dock"
          initial={{ y: 60 }}
          animate={{ y: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        >
          <div className="voice-dock-controls">
            <button
              className="voice-btn"
              onClick={onRepeat}
              title={t.repeatQuestion}
            >
              <Repeat size={20} />
            </button>

            {isSpeaking && !isPaused ? (
              <button className="voice-btn" onClick={pause} title={t.pauseVoice}>
                <Pause size={20} />
              </button>
            ) : isSpeaking && isPaused ? (
              <button className="voice-btn" onClick={resume} title={t.resumeVoice}>
                <Play size={20} />
              </button>
            ) : (
              <button className="voice-btn" onClick={() => {}} disabled>
                <Volume2 size={20} />
              </button>
            )}

            <button
              className="voice-btn voice-btn-danger"
              onClick={() => { stop(); toggleEnabled(); }}
              title={t.stopVoice}
            >
              <Square size={20} />
            </button>
          </div>
        </motion.div>
      )}
      <VoicePrivacyConsent open={showConsent} onAllow={handleConsentAllow} onDeny={handleConsentDeny} />
    </>
  );
}
