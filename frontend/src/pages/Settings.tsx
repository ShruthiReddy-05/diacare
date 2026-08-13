import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUserStore } from '../stores/useUserStore';
import { translations } from '../data/translations';
import { db } from '../services/storage/localDb';
import api from '../services/api/client';
import { subscribeToPush, unsubscribeFromPush, getPushSubscriptionStatus } from '../services/push/subscribe';
import AppBar from '../components/common/AppBar';
import BottomNav from '../components/common/BottomNav';
import LanguageToggle from '../components/common/LanguageToggle';
import { Copy, Trash2, ChevronRight, ChevronDown, User, Info, Bell, Sun, Moon } from 'lucide-react';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export default function Settings() {
  const navigate = useNavigate();
  const { language, user, logout, theme, setTheme } = useUserStore();
  const t = translations[language];
  const [copied, setCopied] = useState(false);

  const [reminders, setReminders] = useState<any[]>([]);
  const [exerciseEnabled, setExerciseEnabled] = useState(false);
  const [exerciseDays, setExerciseDays] = useState<number[]>([1, 3, 5]);
  const [sugarEnabled, setSugarEnabled] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pushStatus, setPushStatus] = useState<'granted' | 'denied' | 'prompt' | 'loading'>('loading');
  const [pushSubscribed, setPushSubscribed] = useState(false);
  const [subscribing, setSubscribing] = useState(false);
  const [exOpen, setExOpen] = useState(false);
  const [sugarOpen, setSugarOpen] = useState(false);

  useEffect(() => {
    getPushSubscriptionStatus().then(setPushStatus);
    navigator.serviceWorker?.ready.then(reg =>
      reg.pushManager.getSubscription().then(sub => setPushSubscribed(!!sub))
    ).catch(() => {});
  }, []);

  const handleSubscribe = async () => {
    if (!user) return;
    setSubscribing(true);
    const ok = await subscribeToPush(user.id);
    if (ok) setPushSubscribed(true);
    setSubscribing(false);
  };

  const handleUnsubscribe = async () => {
    if (!user) return;
    setSubscribing(true);
    const ok = await unsubscribeFromPush(user.id);
    if (ok) setPushSubscribed(false);
    setSubscribing(false);
  };

  useEffect(() => {
    if (!user) return;
    api.getReminders(user.id).then((data) => {
      setReminders(data);
      const ex = data.find((r: any) => r.type === 'exercise');
      if (ex) {
        setExerciseEnabled(ex.is_enabled);
        if (ex.days_of_week) setExerciseDays(ex.days_of_week);
      }
      const sg = data.find((r: any) => r.type === 'sugar_test');
      if (sg) setSugarEnabled(sg.is_enabled);
    }).catch(() => {});
  }, [user]);

  const saveExerciseReminder = async () => {
    if (!user) return;
    setSaving(true);
    const existing = reminders.find((r: any) => r.type === 'exercise');
    const data = {
      type: 'exercise',
      days_of_week: exerciseDays,
      is_enabled: exerciseEnabled,
    };
    try {
      if (existing) {
        await api.updateReminder(user.id, existing.id, data);
      } else {
        await api.createReminder(user.id, data);
      }
    } catch (e: unknown) {
      console.error('Failed to save exercise reminder', e);
    }
    setSaving(false);
  };

  const saveSugarReminder = async () => {
    if (!user) return;
    setSaving(true);
    const existing = reminders.find((r: any) => r.type === 'sugar_test');
    const data = {
      type: 'sugar_test',
      interval_days: 30,
      is_enabled: sugarEnabled,
    };
    try {
      if (existing) {
        await api.updateReminder(user.id, existing.id, data);
      } else {
        await api.createReminder(user.id, data);
      }
    } catch (e: unknown) {
      console.error('Failed to save sugar reminder', e);
    }
    setSaving(false);
  };

  const toggleDay = (day: number) => {
    setExerciseDays(prev =>
      prev.includes(day) ? prev.filter(d => d !== day) : [...prev, day]
    );
  };

  const handleCopy = () => {
    if (user?.display_user_id) {
      navigator.clipboard.writeText(user.display_user_id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleClearData = async () => {
    await logout();
    await db.assessmentSessions.clear();
    await db.sugarReadings.clear();
    await db.activityLogs.clear();
    navigate('/');
  };

  return (
    <div className="page-container">
      <AppBar title={t.settings} />
      <main className="page-content">
        <div className="settings-section">
          <h3 className="settings-section-title">
            <Bell size={18} /> {t.reminders || 'Reminders'}
          </h3>
          <div className="settings-card-clickable" onClick={() => setExOpen(o => !o)}>
            <div className="settings-row">
              <span className="settings-label">{t.reminderExercise || 'Exercise Reminder'}</span>
              <ChevronDown size={18} className={`chevron-rotate ${exOpen ? 'open' : ''}`} />
            </div>
            {exOpen && (
              <div className="settings-card-expanded" onClick={e => e.stopPropagation()}>
                <div className="settings-row" style={{ padding: '8px 0' }}>
                  <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{t.reminderEnable || 'Enable'}</span>
                  <label className="toggle-label">
                    <input type="checkbox" checked={exerciseEnabled} onChange={(e) => setExerciseEnabled(e.target.checked)} />
                    <span className="toggle-slider" />
                  </label>
                </div>
                {exerciseEnabled && (
                  <>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {DAYS.map((day, i) => (
                        <button key={day}
                          className={`scale-chip ${exerciseDays.includes(i) ? 'active' : ''}`}
                          onClick={() => toggleDay(i)} style={{ padding: '4px 10px', fontSize: 12 }}>
                          {day}
                        </button>
                      ))}
                    </div>
                    <button className="btn-primary" onClick={saveExerciseReminder} disabled={saving} style={{ padding: '6px 16px', fontSize: 13, alignSelf: 'flex-end' }}>
                      {saving ? '...' : t.save}
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
          <div className="settings-card-clickable" style={{ marginTop: 8 }} onClick={() => setSugarOpen(o => !o)}>
            <div className="settings-row">
              <span className="settings-label">{t.reminderSugar || 'Sugar Test Reminder'}</span>
              <ChevronDown size={18} className={`chevron-rotate ${sugarOpen ? 'open' : ''}`} />
            </div>
            {sugarOpen && (
              <div className="settings-card-expanded" onClick={e => e.stopPropagation()}>
                <div className="settings-row" style={{ padding: '8px 0' }}>
                  <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{t.reminderEnable || 'Enable'}</span>
                  <label className="toggle-label">
                    <input type="checkbox" checked={sugarEnabled} onChange={(e) => setSugarEnabled(e.target.checked)} />
                    <span className="toggle-slider" />
                  </label>
                </div>
                {sugarEnabled && (
                  <div style={{ padding: '4px 0' }}>
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>{t.reminderMonthly || 'Monthly (1st of month)'}</p>
                    <button className="btn-primary" onClick={saveSugarReminder} disabled={saving} style={{ padding: '6px 16px', fontSize: 13, alignSelf: 'flex-end' }}>
                      {saving ? '...' : t.save}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
          <div className="settings-card" style={{ marginTop: 8 }}>
            {pushStatus === 'loading' ? null : (
              <div className="settings-row">
                <Bell size={18} />
                <span style={{ flex: 1, fontSize: 14 }}>{t.enableNotifications || 'Notifications'}</span>
                <label className="toggle-label">
                  <input type="checkbox"
                    checked={pushSubscribed}
                    disabled={subscribing}
                    onChange={async (e) => {
                      if (e.target.checked) await handleSubscribe();
                      else await handleUnsubscribe();
                    }} />
                  <span className="toggle-slider" />
                </label>
              </div>
            )}
          </div>
        </div>

        <div className="settings-section">
          <h3 className="settings-section-title">
            <User size={18} /> Profile
          </h3>
          <div className="settings-card">
            <div className="settings-row">
              <span className="settings-label">{t.saveThisId}</span>
              <div className="settings-id-row">
                <code className="display-id-small">{user?.display_user_id}</code>
                <button className="icon-btn-sm" onClick={handleCopy}>
                  {copied ? <span className="copy-success">{t.copied}</span> : <Copy size={16} />}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="settings-section">
          <h3 className="settings-section-title">
            <Info size={18} /> Language
          </h3>
          <div className="settings-card">
            <div className="settings-row">
              <span className="settings-label">{t.preferredLanguage}</span>
              <LanguageToggle />
            </div>
          </div>
        </div>

        <div className="settings-section">
          <h3 className="settings-section-title">
            {theme === 'dark' ? <Moon size={18} /> : <Sun size={18} />} {t.theme || 'Theme'}
          </h3>
          <div className="settings-card">
            <div className="settings-row">
              <span className="settings-label">{t.darkMode || 'Dark Mode'}</span>
              <label className="toggle-label toggle-lg">
                <input type="checkbox" checked={theme === 'dark'} onChange={(e) => setTheme(e.target.checked ? 'dark' : 'light')} />
                <span className="toggle-slider" />
              </label>
            </div>
          </div>
        </div>

        <div className="settings-section">
          <h3 className="settings-section-title">
            <Trash2 size={18} /> Data
          </h3>
          <div className="settings-card">
            <button className="settings-danger-btn" disabled onClick={handleClearData}>
              <div>
                <p className="danger-title">{t.clearData}</p>
                <p className="danger-desc">{t.clearDataDesc}</p>
              </div>
              <ChevronRight size={20} />
            </button>
          </div>
        </div>

        <div className="settings-footer">
          <p className="disclaimer">DiaFit Coach v2.0 — Not a substitute for medical advice.</p>
          <p className="disclaimer-small">Data is stored locally on your device and on the server.</p>
        </div>
      </main>
      <BottomNav />
    </div>
  );
}
