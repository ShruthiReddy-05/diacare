import { useState, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import type { AiExercisePrescription } from '../../domain/types';
import { useUserStore } from '../../stores/useUserStore';
import { translations } from '../../data/translations';
import ActivityPlanCard from './ActivityPlanCard';
import StrengthCard from './StrengthCard';
import TipsCard from './TipsCard';
import { AlertTriangle, Play, Pause, RotateCcw, Loader2 } from 'lucide-react';
import api from '../../services/api/client';

interface Props {
  prescription: AiExercisePrescription;
  prescriptionId?: string | null;
}

export default function PrescriptionView({ prescription, prescriptionId }: Props) {
  const { language } = useUserStore();
  const t = translations[language];
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [assetId, setAssetId] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const getOrCreateTts = useCallback(async () => {
    if (assetId || !prescriptionId) return assetId;
    setLoading(true);
    setError('');
    try {
      const lang = language === 'ta' ? 'ta-IN' : 'en-IN';
      const res = await api.getPrescriptionTts(prescriptionId, lang);
      setAssetId(res.asset_id);
      return res.asset_id;
    } catch (e: any) {
      setError(e.message || 'Failed to generate audio');
      return null;
    } finally {
      setLoading(false);
    }
  }, [assetId, prescriptionId, language]);

  const handlePlayPause = async () => {
    if (playing) {
      audioRef.current?.pause();
      setPlaying(false);
      return;
    }
    if (!prescriptionId) { setError('Prescription ID not available'); return; }
    const aid = await getOrCreateTts();
    if (!aid) return;
    const url = api.getTemporaryAudioUrl(aid);
    if (!audioRef.current) {
      audioRef.current = new Audio(url);
      audioRef.current.onended = () => setPlaying(false);
      audioRef.current.onerror = () => { setError('Playback failed'); setPlaying(false); };
    } else {
      audioRef.current.src = url;
    }
    audioRef.current.play().then(() => setPlaying(true)).catch(() => setError('Playback failed'));
  };

  const handleStop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setPlaying(false);
  };

  return (
    <motion.div
      className="prescription-view"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {prescription.medicalClearanceRequired && (
        <div className="medical-clearance-banner">
          <AlertTriangle size={24} />
          <div>
            <strong>{t.medicalClearanceAlert}</strong>
            <p>{t.medicalClearanceDesc}</p>
          </div>
        </div>
      )}

      {!prescription.medicalClearanceRequired && (
        <>
          <div className="prescription-audio-bar">
            <button className="prescription-audio-btn" onClick={handlePlayPause} disabled={loading}>
              {loading ? <Loader2 size={20} className="spin" /> : playing ? <Pause size={20} /> : <Play size={20} />}
            </button>
            <button className="prescription-audio-btn" onClick={handleStop} disabled={loading || !assetId}>
              <RotateCcw size={18} />
            </button>
            <span className="prescription-audio-label">
              {loading ? 'Generating audio...' : playing ? 'Playing...' : 'Listen to plan'}
            </span>
            {error && <span className="prescription-audio-error">{error}</span>}
          </div>

          <ActivityPlanCard
            title={t.planSection1}
            exercises={[...(prescription.activityPlan || []), ...(prescription.simpleActivities || [])]}
          />

          <StrengthCard
            title={t.planSection2}
            exercises={prescription.strengthExercises || []}
          />

          <TipsCard
            title={t.planSection3}
            tips={prescription.personalizedTips || []}
            safetyWarnings={prescription.safetyWarnings}
          />
        </>
      )}
    </motion.div>
  );
}
