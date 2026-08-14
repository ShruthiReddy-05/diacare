import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useUserStore } from '../stores/useUserStore';
import { translations } from '../data/translations';
import api from '../services/api/client';
import AppBar from '../components/common/AppBar';
import BottomNav from '../components/common/BottomNav';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { Plus, X, Droplets } from 'lucide-react';

type BaselineValue = { reading_type: string; value: number };

const READING_TYPES = ['fasting', 'post_meal', 'hba1c'] as const;

function extractBaseline(sessions: any[]): BaselineValue[] {
  const completed = sessions.filter((s: any) => s.status === 'completed');
  const result: BaselineValue[] = [];
  for (const session of completed) {
    for (const r of session.responses || []) {
      if (r.question_id === 'hba1c') {
        const v = parseFloat(r.answer_value);
        if (!isNaN(v)) result.push({ reading_type: 'hba1c', value: v });
      }
      if (r.question_id === 'fasting_sugar') {
        const v = parseFloat(r.answer_value);
        if (!isNaN(v)) result.push({ reading_type: 'fasting', value: v });
      }
    }
  }
  return result;
}

export default function SugarTracking() {
  const navigate = useNavigate();
  const { language, user } = useUserStore();
  const t = translations[language];

  const [readings, setReadings] = useState<any[]>([]);
  const [baseline, setBaseline] = useState<BaselineValue[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [type, setType] = useState<string>('fasting');
  const [value, setValue] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) { navigate('/'); return; }
    Promise.all([
      api.getUserSugarReadings(user.id),
      api.getUserConversationSessions(user.id),
    ]).then(([r, sessions]) => {
      setReadings(r);
      setBaseline(extractBaseline(sessions));
    }).catch(() => {}).finally(() => setLoading(false));
  }, [user]);

  const handleSave = async () => {
    if (!user || !value) return;
    setSaving(true);
    setError('');
    try {
      const data = await api.addSugarReading(user.id, {
        reading_type: type,
        value: parseFloat(value),
        notes: notes || undefined,
      });
      setReadings(prev => [data, ...prev]);
      setShowForm(false);
      setValue('');
      setNotes('');
    } catch (e: any) {
      setError(e.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const readingLabel = (rt: string) => {
    switch (rt) {
      case 'fasting': return t.fasting;
      case 'post_meal': return t.postMeal;
      case 'hba1c': return t.hba1cLabel;
      default: return rt;
    }
  };

  const formatDate = (d: string) => {
    const dt = new Date(d);
    return dt.toLocaleString(language === 'ta' ? 'ta-IN' : 'en-IN');
  };

  return (
    <div className="page-container">
      <AppBar title={t.sugar} showBack onBack={() => navigate('/home')} />

      <main className="page-content">
        {loading && <LoadingSpinner text="Loading..." />}

        {!loading && readings.length === 0 && baseline.length === 0 && !showForm && (
          <motion.div className="empty-state" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <Droplets size={48} className="empty-icon" />
            <p>{t.noReadings}</p>
            <button className="btn-primary" onClick={() => setShowForm(true)}>
              <Plus size={18} /> {t.addSugarReading}
            </button>
          </motion.div>
        )}

        {!loading && baseline.length > 0 && (
          <>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>{t.baselineAssessment || 'Baseline (Initial Assessment)'}</p>
            <div className="readings-list" style={{ marginBottom: 16 }}>
              {baseline.map((b, i) => (
                <div key={`bl-${i}`} className="reading-card" style={{ opacity: 0.7 }}>
                  <div className="reading-value">
                    <strong>{b.value}{b.reading_type === 'hba1c' ? '%' : ' mg/dL'}</strong>
                  </div>
                  <div className="reading-meta">
                    <span className="reading-type">{readingLabel(b.reading_type)}</span>
                    <span className="reading-date">{t.baseline || 'Baseline'}</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {!loading && readings.length > 0 && (
          <div className="readings-list">
            {readings.map((r: any) => (
              <motion.div key={r.id} className="reading-card" layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                <div className="reading-value">
                  <strong>{r.value}{r.reading_type === 'hba1c' ? '%' : ' mg/dL'}</strong>
                </div>
                <div className="reading-meta">
                  <span className="reading-type">{readingLabel(r.reading_type)}</span>
                  <span className="reading-date">{formatDate(r.recorded_at)}</span>
                </div>
                {r.notes && <p className="reading-notes">{r.notes}</p>}
              </motion.div>
            ))}
          </div>
        )}

        {!loading && (readings.length > 0 || baseline.length > 0) && (
          <button className="btn-secondary add-btn" onClick={() => setShowForm(true)}>
            <Plus size={18} /> {t.addSugarReading}
          </button>
        )}
      </main>

      <AnimatePresence>
        {showForm && (
          <motion.div className="modal-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <motion.div className="modal-content" initial={{ y: 200 }} animate={{ y: 0 }} exit={{ y: 200 }} transition={{ type: 'spring', damping: 25 }}>
              <div className="modal-header">
                <h3>{t.addSugarReading}</h3>
                <button className="modal-close" onClick={() => setShowForm(false)}><X size={20} /></button>
              </div>

              <div className="form-group">
                <label>{t.readingType}</label>
                <select value={type} onChange={e => setType(e.target.value)} className="form-select">
                  {READING_TYPES.map(rt => (
                    <option key={rt} value={rt}>{readingLabel(rt)}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>{t.sugarValue}</label>
                <input
                  type="number"
                  step="0.1"
                  className="form-input"
                  placeholder={type === 'hba1c' ? 'e.g. 7.2' : 'e.g. 120'}
                  value={value}
                  onChange={e => setValue(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>{t.notes}</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder={t.notesPlaceholder || 'e.g. Before breakfast'}
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                />
              </div>

              {error && <p className="form-error">{error}</p>}

              <button className="btn-primary" onClick={handleSave} disabled={saving || !value}>
                {saving ? 'Saving...' : t.save}
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <BottomNav />
    </div>
  );
}
