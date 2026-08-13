import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useUserStore } from '../stores/useUserStore';
import { translations } from '../data/translations';
import api from '../services/api/client';
import AppBar from '../components/common/AppBar';
import BottomNav from '../components/common/BottomNav';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { getNotifEventId, markActionCompleted, clearNotifEventId, markLatestActionCompleted } from '../services/notifTracker';
import { ArrowRight, CheckCircle, AlertTriangle } from 'lucide-react';

type Question = {
  id: string;
  key: string;
  label: string;
  type: 'yesno' | 'scale';
};

export default function FollowUp() {
  const navigate = useNavigate();
  const { language, user } = useUserStore();
  const t = translations[language];

  const [loading, setLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<'escalated' | 'positive' | null>(null);

  const questions: Question[] = [
    { id: 'q1_walked', key: 'qWalked', label: t.qWalked || 'Did you walk this week?', type: 'yesno' },
    { id: 'q2_difficulty', key: 'qDifficulty', label: t.qDifficulty || 'How difficult was your exercise this week?', type: 'scale' },
    { id: 'q3_chest_pain_dizziness', key: 'qChestPain', label: t.qChestPain || 'Did you experience chest pain, dizziness, or severe fatigue?', type: 'yesno' },
    { id: 'q4_foot_wounds', key: 'qFootWounds', label: t.qFootWounds || 'Did you notice any foot wounds or swelling?', type: 'yesno' },
  ];

  useEffect(() => {
    if (!user) { navigate('/'); return; }
    api.getNextFollowUp(user.id).then((data: any) => {
      if (data.status === 'due' || data.status === 'overdue') {
        setSessionId(data.session.id);
      } else {
        setResult('positive');
      }
    }).catch(() => {}).finally(() => setLoading(false));
  }, [user]);

  const handleAnswer = (value: any) => {
    const q = questions[step];
    const newAnswers = { ...answers, [q.id]: value };
    setAnswers(newAnswers);

    if (step < questions.length - 1) {
      setStep(step + 1);
    } else {
      handleSubmit(newAnswers);
    }
  };

  const handleSubmit = async (finalAnswers: Record<string, any>) => {
    if (!user || !sessionId) return;
    setSubmitting(true);
    try {
      const data = await api.completeFollowUp(sessionId, {
        q1_walked: finalAnswers.q1_walked ?? null,
        q2_difficulty: finalAnswers.q2_difficulty ?? null,
        q3_chest_pain_dizziness: finalAnswers.q3_chest_pain_dizziness ?? null,
        q4_foot_wounds: finalAnswers.q4_foot_wounds ?? null,
      });
      setResult(data.safety_flag ? 'escalated' : 'positive');
      const notifId = getNotifEventId();
      if (notifId) {
        markActionCompleted(notifId);
        clearNotifEventId();
      } else {
        markLatestActionCompleted(user.id, 'follow_up');
      }
    } catch {
      setResult('positive');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <AppBar title={t.followUp || 'Check-In'} showBack onBack={() => navigate('/home')} />
        <LoadingSpinner />
        <BottomNav />
      </div>
    );
  }

  if (result === 'positive') {
    return (
      <div className="page-container">
        <AppBar title={t.followUp || 'Check-In'} showBack onBack={() => navigate('/home')} />
        <main className="page-content" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20, textAlign: 'center', paddingTop: 60 }}>
          <CheckCircle size={64} color="var(--success)" />
          <h2 style={{ fontSize: 22 }}>{t.positiveTitle || "You're doing well!"}</h2>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>{t.positiveBody || 'Keep up the good work. Continue following your exercise plan.'}</p>
          <button className="btn-primary" onClick={() => navigate('/home')} style={{ marginTop: 16 }}>
            {t.home || 'Home'} <ArrowRight size={18} />
          </button>
        </main>
        <BottomNav />
      </div>
    );
  }

  if (result === 'escalated') {
    return (
      <div className="page-container">
        <AppBar title={t.followUp || 'Check-In'} showBack onBack={() => navigate('/home')} />
        <main className="page-content" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20, textAlign: 'center', paddingTop: 60 }}>
          <AlertTriangle size={64} color="var(--error)" />
          <h2 style={{ fontSize: 22, color: 'var(--error)' }}>{t.escalationTitle || 'Please consult your doctor'}</h2>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>{t.escalationBody || 'Based on your responses, we recommend you stop exercising and consult your doctor immediately.'}</p>
          <button className="btn-primary" onClick={() => navigate('/home')} style={{ marginTop: 16 }}>
            {t.home || 'Home'} <ArrowRight size={18} />
          </button>
        </main>
        <BottomNav />
      </div>
    );
  }

  const q = questions[step];

  return (
    <div className="page-container">
      <AppBar title={t.followUp || 'Check-In'} showBack onBack={() => navigate('/home')} />
      <main className="page-content" style={{ display: 'flex', flexDirection: 'column', gap: 32, paddingTop: 32 }}>
        <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
          {questions.map((_, i) => (
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
            <h3 style={{ fontSize: 20, lineHeight: 1.4, textAlign: 'center' }}>{q.label}</h3>

            {q.type === 'yesno' && (
              <div style={{ display: 'flex', gap: 12 }}>
                <button
                  className={`btn-${answers[q.id] === true ? 'primary' : 'secondary'}`}
                  onClick={() => handleAnswer(true)}
                  style={{ flex: 1 }}
                >
                  Yes
                </button>
                <button
                  className={`btn-${answers[q.id] === false ? 'primary' : 'secondary'}`}
                  onClick={() => handleAnswer(false)}
                  style={{ flex: 1 }}
                >
                  No
                </button>
              </div>
            )}

            {q.type === 'scale' && (
              <div className="scale-row" style={{ justifyContent: 'center' }}>
                {[1, 2, 3, 4, 5].map(n => (
                  <button
                    key={n}
                    className={`scale-chip ${answers[q.id] === n ? 'active' : ''}`}
                    onClick={() => handleAnswer(n)}
                    style={{ minWidth: 60, padding: '12px 8px' }}
                  >
                    {n}
                  </button>
                ))}
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
