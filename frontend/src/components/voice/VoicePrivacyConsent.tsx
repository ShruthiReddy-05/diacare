import { motion, AnimatePresence } from 'framer-motion';
import { Mic, X } from 'lucide-react';
interface Props {
  open: boolean;
  onAllow: () => void;
  onDeny: () => void;
}

export default function VoicePrivacyConsent({ open, onAllow, onDeny }: Props) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="voice-consent-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="voice-consent-modal"
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
          >
            <button className="voice-consent-close" onClick={onDeny}>
              <X size={18} />
            </button>
            <div className="voice-consent-icon">
              <Mic size={28} />
            </div>
            <h3 className="voice-consent-title">Voice Coach</h3>
            <p className="voice-consent-text">
              The voice coach uses your microphone for speech recognition. Audio is processed locally on your device or sent to our server for Tamil speech recognition. No voice recordings are stored permanently.
            </p>
            <div className="voice-consent-actions">
              <button className="btn-primary" onClick={onAllow}
                style={{ padding: '10px 24px', fontSize: 14 }}>
                Allow
              </button>
              <button className="voice-consent-skip" onClick={onDeny}>
                Not now
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
