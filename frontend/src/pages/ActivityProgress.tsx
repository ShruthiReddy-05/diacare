import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useUserStore } from '../stores/useUserStore';
import { translations } from '../data/translations';
import api from '../services/api/client';
import AppBar from '../components/common/AppBar';
import BottomNav from '../components/common/BottomNav';
import LoadingSpinner from '../components/common/LoadingSpinner';
import StatusCard from '../components/home/StatusCard';
import { Plus, X, Activity, TrendingUp, Zap, AlertTriangle } from 'lucide-react';

function getWeekStart(d = new Date()): string {
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  const monday = new Date(d.setDate(diff));
  return monday.toISOString().slice(0, 10);
}

export default function ActivityProgress() {
  const navigate = useNavigate();
  const { language, user } = useUserStore();
  const t = translations[language];

  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [weekStart, setWeekStart] = useState(getWeekStart());
  const [days, setDays] = useState('');
  const [minutes, setMinutes] = useState('');
  const [fatigue, setFatigue] = useState<number>(1);
  const [difficulty, setDifficulty] = useState<number>(1);
  const [strengthDone, setStrengthDone] = useState(false);
  const [safetyIssue, setSafetyIssue] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) { navigate('/'); return; }
    api.getUserActivityLogs(user.id)
      .then(setLogs)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  const totalMinutes = logs.reduce((sum: number, l: any) => sum + (l.completed_minutes || 0), 0);
  const totalDays = logs.reduce((sum: number, l: any) => sum + (l.completed_days || 0), 0);
  const safetyFlags = logs.filter((l: any) => l.safety_flag).length;

  const handleSave = async () => {
    if (!user || !days || !minutes) return;
    setSaving(true);
    setError('');
    try {
      const data = await api.logActivity(user.id, {
        activity_date: weekStart,
        completed_minutes: parseInt(minutes) || 0,
        completed_days: parseInt(days) || 0,
        strength_completed: strengthDone,
        fatigue_rating: fatigue,
        difficulty_rating: difficulty,
        safety_flag: safetyIssue,
        notes: safetyIssue ? 'Safety flag triggered' : undefined,
      });
      setLogs(prev => [data, ...prev.filter(l => l.activity_date !== weekStart)]);
      setShowForm(false);
      setDays('');
      setMinutes('');
      setStrengthDone(false);
      setSafetyIssue(false);
    } catch (e: any) {
      setError(e.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const fatigueLabel = (v: number) => {
    if (v <= 2) return t.none;
    if (v <= 3) return t.moderate;
    return t.severe;
  };

  const diffLabel = (v: number) => {
    if (v <= 2) return t.easy;
    if (v <= 3) return t.moderate;
    return t.hard;
  };

  const formatWeek = (d: string) => {
    const dt = new Date(d);
    const opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric' };
    return `${t.weekOf || 'Week of '}${dt.toLocaleDateString(language === 'ta' ? 'ta-IN' : 'en-IN', opts)}`;
  };

  const alreadyLogged = logs.some((l: any) => l.activity_date === weekStart);

  return (
    <div className="page-container">
      <AppBar title={t.activityProgress} showBack onBack={() => navigate('/home')} />

      <main className="page-content">
        {loading && <LoadingSpinner text="Loading..." />}

        {!loading && (
          <>
            <div className="status-cards-grid">
              <StatusCard icon={<Activity size={24} />} title={t.totalMinutes || 'Total Minutes'} value={`${totalMinutes} ${t.minutes}`} color="#10B981" />
              <StatusCard icon={<TrendingUp size={24} />} title={t.activeDays || 'Active Days'} value={`${totalDays} ${t.days}`} color="#3B82F6" />
              <StatusCard icon={<Zap size={24} />} title={t.weeksLogged || 'Weeks Logged'} value={`${logs.length}`} color="#8B5CF6" />
              {safetyFlags > 0 && (
                <StatusCard icon={<AlertTriangle size={24} />} title={t.safetyFlags} value={`${safetyFlags}`} color="#EF4444" />
              )}
            </div>

            {logs.length === 0 && (
              <motion.div className="empty-state" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <Activity size={48} className="empty-icon" />
                <p>{t.emptyHistory}</p>
              </motion.div>
            )}

            {logs.length > 0 && (
              <div className="readings-list">
                {logs.map((l: any) => (
                  <motion.div key={l.id} className="reading-card" layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                    <div className="reading-value">
                      <strong>{l.completed_minutes} {t.minutes} · {l.completed_days} {t.days}</strong>
                    </div>
                    <div className="reading-meta">
                      <span className="reading-type">{formatWeek(l.activity_date)}</span>
                      <span className="reading-date">
                        {t.diff || 'Diff'}: {diffLabel(l.difficulty_rating || 1)} | {t.fatigue}: {fatigueLabel(l.fatigue_rating || 1)}
                        {l.strength_completed ? ` | ${t.strengthCompleted} ✓` : ''}
                        {l.safety_flag ? ` | ⚠️ ${t.safetyIssue}` : ''}
                      </span>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}

            <button
              className={`btn-${alreadyLogged ? 'secondary' : 'primary'} add-btn`}
              onClick={() => setShowForm(true)}
            >
              <Plus size={18} /> {alreadyLogged ? (t.updateWeek || 'Update Week Activity') : (t.logThisWeek || 'Log This Week')}
            </button>
          </>
        )}
      </main>

      <AnimatePresence>
        {showForm && (
          <motion.div className="modal-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <motion.div className="modal-content" initial={{ y: 200 }} animate={{ y: 0 }} exit={{ y: 200 }} transition={{ type: 'spring', damping: 25 }}>
              <div className="modal-header">
                <h3>{t.logActivity}</h3>
                <button className="modal-close" onClick={() => setShowForm(false)}><X size={20} /></button>
              </div>

              <div className="form-group">
                <label>{t.weekStarting || 'Week starting'}</label>
                <input type="date" className="form-input" value={weekStart} onChange={e => setWeekStart(e.target.value)} />
              </div>

              <div className="form-group">
                <label>{t.howManyDays || 'How many days did you exercise this week?'}</label>
                <input type="number" className="form-input" min="0" max="7" placeholder="e.g. 4" value={days} onChange={e => setDays(e.target.value)} />
              </div>

              <div className="form-group">
                <label>{t.totalMinutesQ || 'Total minutes this week?'}</label>
                <input type="number" className="form-input" min="0" placeholder="e.g. 150" value={minutes} onChange={e => setMinutes(e.target.value)} />
              </div>

              <div className="form-group">
                <label>{t.difficulty}</label>
                <div className="scale-row">
                  {[1, 2, 3, 4, 5].map(n => (
                    <button key={n} className={`scale-chip ${difficulty === n ? 'active' : ''}`} onClick={() => setDifficulty(n)}>
                      {n} {diffLabel(n)}
                    </button>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label>{t.fatigue}</label>
                <div className="scale-row">
                  {[1, 2, 3, 4, 5].map(n => (
                    <button key={n} className={`scale-chip ${fatigue === n ? 'active' : ''}`} onClick={() => setFatigue(n)}>
                      {n} {fatigueLabel(n)}
                    </button>
                  ))}
                </div>
              </div>

              <div className="form-group checkbox-row">
                <label>
                  <input type="checkbox" checked={strengthDone} onChange={e => setStrengthDone(e.target.checked)} />
                  {t.strengthCompleted}
                </label>
              </div>

              <div className="form-group checkbox-row">
                <label>
                  <input type="checkbox" checked={safetyIssue} onChange={e => setSafetyIssue(e.target.checked)} />
                  {t.safetyIssue}
                </label>
              </div>

              {error && <p className="form-error">{error}</p>}

              <button className="btn-primary" onClick={handleSave} disabled={saving || !days || !minutes}>
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
