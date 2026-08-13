import { motion } from 'framer-motion';
import { useVoiceCoachStore } from '../../stores/useVoiceCoachStore';
import { Loader2, Mic, Square, Pause, Play, CheckCircle2, AlertCircle } from 'lucide-react';

const stateConfig: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  idle: { icon: <Mic size={16} />, label: 'Voice Coach', color: '#6B7280' },
  loading_audio: { icon: <Loader2 size={16} className="spin" />, label: 'Loading...', color: '#F59E0B' },
  speaking_question: { icon: <Play size={16} />, label: 'Speaking', color: '#10B981' },
  paused: { icon: <Pause size={16} />, label: 'Paused', color: '#F59E0B' },
  listening: { icon: <Mic size={16} className="pulse" />, label: 'Listening...', color: '#3B82F6' },
  confirming_transcript: { icon: <CheckCircle2 size={16} />, label: 'Confirm', color: '#8B5CF6' },
  validating_answer: { icon: <Loader2 size={16} className="spin" />, label: 'Checking...', color: '#F59E0B' },
  advancing: { icon: <Loader2 size={16} className="spin" />, label: 'Next...', color: '#10B981' },
  error: { icon: <AlertCircle size={16} />, label: 'Error', color: '#EF4444' },
  stopped: { icon: <Square size={16} />, label: 'Stopped', color: '#6B7280' },
};

export default function VoiceFlowIndicator() {
  const { flowState } = useVoiceCoachStore();
  const cfg = stateConfig[flowState] || stateConfig.idle;

  return (
    <motion.div
      className="voice-indicator"
      animate={{ borderColor: cfg.color }}
      transition={{ duration: 0.3 }}
    >
      <motion.span
        key={flowState}
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="voice-indicator-icon"
        style={{ color: cfg.color }}
      >
        {cfg.icon}
      </motion.span>
      <span className="voice-indicator-label" style={{ color: cfg.color }}>
        {cfg.label}
      </span>
    </motion.div>
  );
}
