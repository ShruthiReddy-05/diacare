import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useUserStore } from '../stores/useUserStore';
import { translations } from '../data/translations';
import api, { SafetyLockError } from '../services/api/client';
import AppBar from '../components/common/AppBar';
import BottomNav from '../components/common/BottomNav';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { getNotifEventId, markActionCompleted, clearNotifEventId, markLatestActionCompleted } from '../services/notifTracker';
import { ArrowRight, CheckCircle, AlertTriangle } from 'lucide-react';

type Step =
  | { id: 'q1_activity_days'; label: string; kind: 'days0to7' }
  | { id: 'q2_food_goal_days'; label: string; kind: 'days0to7' }
  | { id: 'q3_medication_days'; label: string; kind: 'days0to7' }
  | { id: 'q4_foot_care_days'; label: string; kind: 'days0to7' }
  | { id: 'q5_new_foot_problem'; label: string; kind: 'yesno' }
  | { id: 'q6_stress_0_10'; label: string; kind: 'scale0to10' }
  | { id: 'q7_sleep_0_10'; label: string; kind: 'scale0to10' }
  | { id: 'q8_sugar_reading'; label: string; kind: 'number' }
  | { id: 'q8b_hypo_episode'; label: string; kind: 'yesno' }
  | { id: 'fever_or_vomiting_reported'; label: string; kind: 'yesno' }
  | { id: 'upcoming_function_or_fasting'; label: string; kind: 'yesno' };

export default function CheckIn() {
  const navigate = useNavigate();
  const { language, user } = useUserStore();
  const t = translations[language];

  const [loading, setLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<'escalated' | 'positive' | null>(null);
  const [triggered, setTriggered] = useState<{ sick_day?: boolean; festival_fasting?: boolean } | null>(null);

  const steps: Step[] = [
    { id: 'q1_activity_days', label: t.ciActivityDays, kind: 'days0to7' },
    { id: 'q2_food_goal_days', label: t.ciFoodGoalDays, kind: 'days0to7' },
    { id: 'q3_medication_days', label: t.ciMedicationDays, kind: 'days0to7' },
    { id: 'q4_foot_care_days', label: t.ciFootCareDays, kind: 'days0to7' },
    { id: 'q5_new_foot_problem', label: t.ciNewFootProblem, kind: 'yesno' },
    { id: 'q6_stress_0_10', label: t.ciStress, kind: 'scale0to10' },
    { id: 'q7_sleep_0_10', label: t.ciSleep, kind: 'scale0to10' },
    { id: 'q8_sugar_reading', label: t.ciSugarReading, kind: 'number' },
    { id: 'q8b_hypo_episode', label: t.ciHypoEpisode, kind: 'yesno' },
    { id: 'fever_or_vomiting_reported', label: t.ciFeverVomiting, kind: 'yesno' },
    { id: 'upcoming_function_or_fasting', label: t.ciUpcomingFunction, kind: 'yesno' },
  ];

  useEffect(() => {
    if (!user) { navigate('/'); return; }
    api.getNextCheckIn(user.id).then((data: any) => {
      if (data.status === 'due' || data.status === 'missed') {
        setSessionId(data.session.id);
      } else {
        setResult('positive');
      }
    }).catch(() => {}).finally(() => setLoading(false));
  }, [user]);

  const handleAnswer = (value: any) => {
    const s = steps[step];
    const newAnswers = { ...answers, [s.id]: value };
    setAnswers(newAnswers);

    if (step < steps.length - 1) {
      setStep(step + 1);
    } else {
      handleSubmit(newAnswers);
    }
  };

  const handleSubmit = async (finalAnswers: Record<string, any>) => {
    if (!user || !sessionId) return;
    setSubmitting(true);
    try {
      const data = await api.completeCheckIn(sessionId, {
        q1_activity_days: finalAnswers.q1_activity_days ?? 0,
        q2_food_goal_days: finalAnswers.q2_food_goal_days ?? 0,
        q3_medication_days: finalAnswers.q3_medication_days ?? 0,
        q4_foot_care_days: finalAnswers.q4_foot_care_days ?? 0,
        q5_new_foot_problem: !!finalAnswers.q5_new_foot_problem,
        q6_stress_0_10: finalAnswers.q6_stress_0_10 ?? 0,
        q7_sleep_0_10: finalAnswers.q7_sleep_0_10 ?? 0,
        q8_sugar_reading: finalAnswers.q8_sugar_reading ?? null,
        q8b_hypo_episode: !!finalAnswers.q8b_hypo_episode,
        fever_or_vomiting_reported: !!finalAnswers.fever_or_vomiting_reported,
        upcoming_function_or_fasting: !!finalAnswers.upcoming_function_or_fasting,
      });
      setTriggered(data.triggered_content || null);
      setResult(data.safety_flag ? 'escalated' : 'positive');
      const notifId = getNotifEventId();
      if (notifId) {
        markActionCompleted(notifId);
        clearNotifEventId();
      } else {
        markLatestActionCompleted(user.id, 'checkin');
      }
    } catch (e) {
      // 423: answers were saved and screened, but coaching is locked --
      // SafetyLockGate takes over the screen. Never show "positive" for it.
      setResult(e instanceof SafetyLockError ? 'escalated' : 'positive');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <AppBar title={t.followUp} showBack onBack={() => navigate('/home')} />
        <LoadingSpinner />
        <BottomNav />
      </div>
    );
  }

  if (result === 'positive') {
    return (
      <div className="page-container">
        <AppBar title={t.followUp} showBack onBack={() => navigate('/home')} />
        <main className="page-content" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20, textAlign: 'center', paddingTop: 60 }}>
          <CheckCircle size={64} color="var(--success)" />
          <h2 style={{ fontSize: 22 }}>{t.positiveTitle}</h2>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>{t.positiveBody}</p>
          {triggered?.sick_day && <p className="careplan-warning">{t.sickDayMessage}</p>}
          {triggered?.festival_fasting && <p className="careplan-warning">{t.festivalFastingMessage}</p>}
          <button className="btn-primary" onClick={() => navigate('/home')} style={{ marginTop: 16 }}>
            {t.home} <ArrowRight size={18} />
          </button>
        </main>
        <BottomNav />
      </div>
    );
  }

  if (result === 'escalated') {
    return (
      <div className="page-container">
        <AppBar title={t.followUp} showBack onBack={() => navigate('/home')} />
        <main className="page-content" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20, textAlign: 'center', paddingTop: 60 }}>
          <AlertTriangle size={64} color="var(--error)" />
          <h2 style={{ fontSize: 22, color: 'var(--error)' }}>{t.escalationTitle}</h2>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>{t.escalationBody}</p>
          <button className="btn-primary" onClick={() => navigate('/home')} style={{ marginTop: 16 }}>
            {t.home} <ArrowRight size={18} />
          </button>
        </main>
        <BottomNav />
      </div>
    );
  }

  const s = steps[step];

  return (
    <div className="page-container">
      <AppBar title={t.followUp} showBack onBack={() => navigate('/home')} />
      <main className="page-content" style={{ display: 'flex', flexDirection: 'column', gap: 32, paddingTop: 32 }}>
        <div style={{ display: 'flex', gap: 4, justifyContent: 'center', flexWrap: 'wrap' }}>
          {steps.map((_, i) => (
            <div key={i} style={{
              width: 8, height: 8, borderRadius: '50%',
              background: i === step ? 'var(--primary-light)' : i < step ? 'var(--success)' : 'var(--border)',
            }} />
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 24 }}
          >
            <h3 style={{ fontSize: 20, lineHeight: 1.4, textAlign: 'center' }}>{s.label}</h3>

            {s.kind === 'yesno' && (
              <div style={{ display: 'flex', gap: 12 }}>
                <button
                  className={`btn-${answers[s.id] === true ? 'primary' : 'secondary'}`}
                  onClick={() => handleAnswer(true)}
                  style={{ flex: 1 }}
                >
                  Yes
                </button>
                <button
                  className={`btn-${answers[s.id] === false ? 'primary' : 'secondary'}`}
                  onClick={() => handleAnswer(false)}
                  style={{ flex: 1 }}
                >
                  No
                </button>
              </div>
            )}

            {s.kind === 'days0to7' && (
              <div className="scale-row" style={{ justifyContent: 'center', flexWrap: 'wrap' }}>
                {[0, 1, 2, 3, 4, 5, 6, 7].map(n => (
                  <button
                    key={n}
                    className={`scale-chip ${answers[s.id] === n ? 'active' : ''}`}
                    onClick={() => handleAnswer(n)}
                    style={{ minWidth: 44, padding: '12px 8px' }}
                  >
                    {n}
                  </button>
                ))}
              </div>
            )}

            {s.kind === 'scale0to10' && (
              <div className="scale-row" style={{ justifyContent: 'center', flexWrap: 'wrap' }}>
                {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => (
                  <button
                    key={n}
                    className={`scale-chip ${answers[s.id] === n ? 'active' : ''}`}
                    onClick={() => handleAnswer(n)}
                    style={{ minWidth: 40, padding: '10px 6px' }}
                  >
                    {n}
                  </button>
                ))}
              </div>
            )}

            {s.kind === 'number' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center' }}>
                <input
                  type="number"
                  className="form-input"
                  style={{ maxWidth: 200, textAlign: 'center' }}
                  placeholder="mg/dL"
                  onChange={e => setAnswers(prev => ({ ...prev, [s.id]: e.target.value ? parseFloat(e.target.value) : null }))}
                />
                <button className="btn-primary" onClick={() => handleAnswer(answers[s.id] ?? null)}>
                  {t.continueBtn}
                </button>
              </div>
            )}
          </motion.div>
        </AnimatePresence>

        {submitting && <p style={{ textAlign: 'center', color: 'var(--text-muted)' }}>Saving...</p>}
      </main>
      <BottomNav />
    </div>
  );
}
