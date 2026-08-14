import { useState, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import type { CarePlanSnapshot } from '../../domain/types';
import { useUserStore } from '../../stores/useUserStore';
import { translations } from '../../data/translations';
import { AlertTriangle, Play, Pause, RotateCcw, Loader2, CheckCircle2, Download } from 'lucide-react';
import api from '../../services/api/client';

interface Props {
  plan: CarePlanSnapshot;
  riskTier?: string | null;
  carePlanId?: string | null;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="careplan-section">
      <h3 className="careplan-section-title">{title}</h3>
      {children}
    </div>
  );
}

export default function CarePlanView({ plan, riskTier, carePlanId }: Props) {
  const { language } = useUserStore();
  const t = translations[language];
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [assetId, setAssetId] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const getOrCreateTts = useCallback(async () => {
    if (assetId || !carePlanId) return assetId;
    setLoading(true);
    setError('');
    try {
      const lang = language === 'ta' ? 'ta-IN' : 'en-IN';
      const res = await api.getCarePlanTts(carePlanId, lang);
      setAssetId(res.asset_id);
      return res.asset_id;
    } catch (e: any) {
      setError(e.message || 'Failed to generate audio');
      return null;
    } finally {
      setLoading(false);
    }
  }, [assetId, carePlanId, language]);

  const handlePlayPause = async () => {
    if (playing) {
      audioRef.current?.pause();
      setPlaying(false);
      return;
    }
    if (!carePlanId) { setError('Care plan ID not available'); return; }
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

  const clearanceRequired = plan.activity_plan?.medical_clearance_required;

  return (
    <motion.div
      className="careplan-view"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <p className="careplan-disclaimer">{plan.disclaimer}</p>

      {riskTier === 'red' && (
        <div className="medical-clearance-banner">
          <AlertTriangle size={24} />
          <div>
            <strong>{t.medicalClearanceAlert}</strong>
            <p>{t.medicalClearanceDesc}</p>
          </div>
        </div>
      )}

      <div className="prescription-audio-bar careplan-no-print">
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
        <button className="careplan-download-btn" onClick={() => window.print()} title="Download as PDF">
          <Download size={16} /> Download PDF
        </button>
      </div>

      <Section title={t.clinicalStatus}>
        <div className="careplan-table">
          {plan.clinical_status.rows.map((row, i) => (
            <div key={i} className="careplan-table-row">
              <span className="careplan-table-what">{row.what}</span>
              <span className="careplan-table-value">{row.last_value ?? '--'}</span>
              <span className="careplan-table-target">{row.target}</span>
            </div>
          ))}
        </div>
        <p className="careplan-note">{plan.clinical_status.note}</p>
      </Section>

      <Section title={t.dietaryGoals}>
        <p className="careplan-note">{plan.dietary_goals.intro}</p>
        <ul className="careplan-goal-list">
          {plan.dietary_goals.goals.map((g, i) => (
            <li key={i}><CheckCircle2 size={16} /> {g.text_en}</li>
          ))}
        </ul>
      </Section>

      <Section title={t.activityPlanTitle}>
        {clearanceRequired && (
          <p className="careplan-warning">{plan.activity_plan.medical_clearance_note}</p>
        )}
        {plan.activity_plan.weekly_target && <p className="careplan-note">{plan.activity_plan.weekly_target}</p>}
        {plan.activity_plan.activity_guidance && <p className="careplan-note">{plan.activity_plan.activity_guidance}</p>}
        {plan.activity_plan.ramp_protocol && (
          <div className="careplan-table">
            {plan.activity_plan.ramp_protocol.map((r, i) => (
              <div key={i} className="careplan-table-row">
                <span className="careplan-table-what">{t.weeks ? `${t.weeks} ${r.weeks}` : r.weeks}</span>
                <span className="careplan-table-value">{r.daily_minutes}</span>
                <span className="careplan-table-target">{r.note}</span>
              </div>
            ))}
          </div>
        )}
        {plan.activity_plan.resistance_exercise && (
          <p className="careplan-note">
            {plan.activity_plan.resistance_exercise.activity_name} — {plan.activity_plan.resistance_exercise.duration}, {plan.activity_plan.resistance_exercise.frequency}
          </p>
        )}
        {plan.activity_plan.movement_break_rule && <p className="careplan-note">{plan.activity_plan.movement_break_rule}</p>}
        {plan.activity_plan.foot_precautions && (
          <ul className="careplan-goal-list">
            {plan.activity_plan.foot_precautions.map((p, i) => <li key={i}><AlertTriangle size={16} /> {p}</li>)}
          </ul>
        )}
        {plan.activity_plan.glucose_check_note && <p className="careplan-warning">{plan.activity_plan.glucose_check_note}</p>}
      </Section>

      <Section title={t.sleepAndStress}>
        {plan.sleep_and_stress.sleep_apnea_risk_flag && <p className="careplan-warning">{t.sleepApneaFlag}</p>}
        {plan.sleep_and_stress.coping_strategy && <p className="careplan-note">{plan.sleep_and_stress.coping_strategy}</p>}
      </Section>

      <Section title={t.medicinesTitle}>
        {plan.medicines.reminder_schedule.length > 0 && (
          <div className="careplan-table">
            {plan.medicines.reminder_schedule.map((m, i) => (
              <div key={i} className="careplan-table-row">
                <span className="careplan-table-what">{m.label}</span>
                <span className="careplan-table-value">{m.time_of_day}</span>
              </div>
            ))}
          </div>
        )}
        <p className="careplan-note">{plan.medicines.adherence_boilerplate}</p>
        {plan.medicines.herbal_note && <p className="careplan-warning">{plan.medicines.herbal_note}</p>}
      </Section>

      <Section title={t.monitoringPlan}>
        {plan.monitoring_plan.monitoring_plan && (
          <div className="careplan-table">
            {Object.entries(plan.monitoring_plan.monitoring_plan).map(([k, v]) => (
              <div key={k} className="careplan-table-row">
                <span className="careplan-table-what">{k.replace(/_/g, ' ')}</span>
                <span className="careplan-table-target">{v}</span>
              </div>
            ))}
          </div>
        )}
        {plan.monitoring_plan.next_visit_script && (
          <p className="careplan-note">"{plan.monitoring_plan.next_visit_script}"</p>
        )}
      </Section>

      {plan.conditional_hypo_protocol && (
        <Section title={plan.conditional_hypo_protocol.title}>
          <p className="careplan-note">{plan.conditional_hypo_protocol.protocol_text_en}</p>
          <p className="careplan-warning">{plan.conditional_hypo_protocol.escalation_note}</p>
        </Section>
      )}

      <div className="careplan-escalation">
        <h3 className="careplan-section-title">{plan.escalation.title}</h3>
        <ul className="careplan-goal-list">
          {plan.escalation.bullets.map((b, i) => <li key={i}><AlertTriangle size={16} color="var(--error)" /> {b}</li>)}
        </ul>
      </div>
    </motion.div>
  );
}
