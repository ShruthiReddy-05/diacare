import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useUserStore } from '../../stores/useUserStore';
import { translations } from '../../data/translations';
import api from '../../services/api/client';
import { subscribeToPush, getPushSubscriptionStatus } from '../../services/push/subscribe';
import StatusCard from './StatusCard';
import ActionCard from './ActionCard';
import {
  Activity, Heart, ClipboardList, FileText,
  TrendingUp, Clock, Zap, Droplets, Shield, AlertCircle, CheckCircle, Bell
} from 'lucide-react';

const SITTINGS = ['1', '2', '3'];

function nextSitting(sessions: any[]): { sitting: string; inProgress: boolean } | null {
  const completed = new Set(sessions.filter((s: any) => s.status === 'completed').map((s: any) => s.sitting));
  const inProgress = new Set(sessions.filter((s: any) => s.status === 'in_progress').map((s: any) => s.sitting));
  for (const sitting of SITTINGS) {
    if (!completed.has(sitting)) {
      return { sitting, inProgress: inProgress.has(sitting) };
    }
  }
  return null;
}

export default function HomePage() {
  const navigate = useNavigate();
  const { language, user } = useUserStore();
  const t = translations[language];

  const [pending, setPending] = useState<{ sitting: string; inProgress: boolean } | null>({ sitting: '1', inProgress: false });
  const [allSittingsDone, setAllSittingsDone] = useState(false);
  const [lastSugar, setLastSugar] = useState<string | null>(null);
  const [activeMinutes, setActiveMinutes] = useState(0);
  const [riskTier, setRiskTier] = useState<string | null>(null);
  const [checkIn, setCheckIn] = useState<{ status: string; session: any } | null>(null);
  const [adherenceStreak, setAdherenceStreak] = useState(0);
  const [dismissNotifBanner, setDismissNotifBanner] = useState(true);

  useEffect(() => {
    getPushSubscriptionStatus().then(status => {
      if (status !== 'granted') {
        setDismissNotifBanner(false);
      }
    });
  }, []);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      api.getUserConversationSessions(user.id),
      api.getUserSugarReadings(user.id),
      api.getUserActivityLogs(user.id),
      api.getLatestCarePlan(user.id).catch(() => null),
      api.getNextCheckIn(user.id).catch(() => null),
      api.getCurrentAdherence(user.id).catch(() => null),
    ]).then(([sessions, readings, logs, carePlan, nextCheckIn, adh]) => {
      const next = nextSitting(sessions);
      setPending(next);
      setAllSittingsDone(!next);

      if (readings.length > 0) {
        const nonHba1c = readings.filter((r: any) => r.reading_type !== 'hba1c');
        const chosen = nonHba1c.length > 0
          ? nonHba1c[nonHba1c.length - 1]
          : readings[readings.length - 1];
        setLastSugar(`${chosen.value}${chosen.reading_type === 'hba1c' ? '%' : ' mg/dL'}`);
      }

      const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
      const weekLogs = logs.filter((l: any) => new Date(l.activity_date) >= weekAgo);
      const total = weekLogs.reduce((sum: number, l: any) => sum + (l.completed_minutes || 0), 0);
      setActiveMinutes(total);

      if (carePlan?.risk_tier) setRiskTier(carePlan.risk_tier);
      if (nextCheckIn) setCheckIn(nextCheckIn);
      if (adh) setAdherenceStreak(adh.activity_streak_weeks || 0);
    }).catch(() => {});
  }, [user]);

  const checkInStatus = (() => {
    if (!checkIn || checkIn.status === 'none') return null;
    if (checkIn.status === 'due' || checkIn.status === 'missed') {
      return { icon: <AlertCircle size={24} />, color: checkIn.status === 'missed' ? '#EF4444' : '#F59E0B', title: checkIn.status === 'missed' ? t.followUpOverdue : t.followUpDue };
    }
    return { icon: <CheckCircle size={24} />, color: '#10B981', title: t.followUpCompleted };
  })();

  const riskColor = riskTier === 'red' ? '#EF4444' : riskTier === 'amber' ? '#F59E0B' : riskTier === 'green' ? '#10B981' : '#8B5CF6';

  return (
    <div className="home-page">
      {!dismissNotifBanner && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="notif-topbar"
        >
          <Bell size={16} />
          <span style={{ flex: 1, fontSize: 12, lineHeight: 1.3 }}>
            {t.notifPrompt}
            <span style={{ display: 'block', fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>
              {t.notifChangeSettings}
            </span>
          </span>
          <button className="btn-primary" onClick={() => {
            setDismissNotifBanner(true);
            sessionStorage.setItem('df_notif_dismissed', '1');
            if (user) subscribeToPush(user.id);
          }} style={{ padding: '3px 10px', fontSize: 11, whiteSpace: 'nowrap', width: 'auto' }}>
            {t.reminderEnable}
          </button>
          <button onClick={() => {
            setDismissNotifBanner(true);
            sessionStorage.setItem('df_notif_dismissed', '1');
          }} style={{ padding: '3px 10px', fontSize: 11, whiteSpace: 'nowrap', background: 'none', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', color: 'var(--text-muted)', cursor: 'pointer' }}>
            Not Allow
          </button>
        </motion.div>
      )}
      <motion.div
        className="home-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="greeting">
          <Heart size={20} className="greeting-icon" />
          <h2>{t.tagline}</h2>
        </div>
        {user && (
          <p className="user-display-id">{user.display_user_id}</p>
        )}
      </motion.div>

      <div className="status-cards-grid">
        <StatusCard
          icon={<Activity size={24} />}
          title={t.activeMinutes}
          value={`${activeMinutes} ${t.minutes}`}
          color="#10B981"
        />
        <StatusCard
          icon={<TrendingUp size={24} />}
          title={t.latestSugar}
          value={lastSugar || '--'}
          color="#F59E0B"
        />
        <StatusCard
          icon={<Clock size={24} />}
          title={t.adherenceStreak}
          value={`${adherenceStreak} ${t.weeks}`}
          color="#3B82F6"
        />
        {checkInStatus && (
          <StatusCard
            icon={checkInStatus.icon}
            title={t.followUp}
            value={checkInStatus.title}
            color={checkInStatus.color}
          />
        )}
        <StatusCard
          icon={<Zap size={24} />}
          title={t.riskCategory}
          value={riskTier || '--'}
          color={riskColor}
        />
      </div>

      <div className="action-cards">
        {pending ? (
          <ActionCard
            icon={<ClipboardList size={24} />}
            title={pending.inProgress ? `${t.resumeAssessment} ${pending.sitting}` : `${t.startAssessment} ${pending.sitting}`}
            description={t.descAssessment}
            onClick={() => navigate(`/conversation/${pending.sitting}`)}
            color={pending.inProgress ? '#F59E0B' : '#2C6E49'}
          />
        ) : (
          <ActionCard
            icon={<FileText size={24} />}
            title={t.viewPlan}
            description={t.descPlan}
            onClick={() => navigate('/care-plan/latest')}
            color="#2C6E49"
          />
        )}

        <ActionCard
          icon={<Activity size={24} />}
          title={t.logActivity}
          description={t.descActivity}
          onClick={() => navigate('/activity')}
          color="#3B82F6"
        />

        <ActionCard
          icon={<Droplets size={24} />}
          title={t.addSugarReading}
          description={t.descSugar}
          onClick={() => navigate('/sugar')}
          color="#F59E0B"
        />

        {allSittingsDone && (
          <ActionCard
            icon={<Shield size={24} />}
            title={t.followUp}
            description={checkInStatus ? checkInStatus.title : t.followUp}
            onClick={() => navigate('/check-in')}
            color="#8B5CF6"
          />
        )}
      </div>

      <div className="home-footer">
        <p className="disclaimer">{t.disclaimer}</p>
      </div>
    </div>
  );
}
