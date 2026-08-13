import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useUserStore } from '../../stores/useUserStore';
import { useAssessmentStore } from '../../stores/useAssessmentStore';
import { translations } from '../../data/translations';
import api from '../../services/api/client';
import { subscribeToPush, getPushSubscriptionStatus } from '../../services/push/subscribe';
import StatusCard from './StatusCard';
import ActionCard from './ActionCard';
import {
  Activity, Heart, ClipboardList, FileText,
  TrendingUp, Clock, Zap, Droplets, Shield, AlertCircle, CheckCircle, Bell
} from 'lucide-react';

export default function HomePage() {
  const navigate = useNavigate();
  const { language, user } = useUserStore();
  const { isComplete } = useAssessmentStore();
  const t = translations[language];

  const [hasAssessment, setHasAssessment] = useState(false);
  const [hasInProgress, setHasInProgress] = useState(false);
  const [lastSugar, setLastSugar] = useState<string | null>(null);
  const [activeMinutes, setActiveMinutes] = useState(0);
  const [riskLevel, setRiskLevel] = useState<string | null>(null);
  const [followUp, setFollowUp] = useState<{ status: string; session: any } | null>(null);
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
      api.getUserAssessments(user.id),
      api.getUserSugarReadings(user.id),
      api.getUserActivityLogs(user.id),
      api.getNextFollowUp(user.id).catch(() => null),
      api.getCurrentAdherence(user.id).catch(() => null),
    ]).then(([sessions, readings, logs, fu, adh]) => {
      if (sessions.length > 0) {
        setHasAssessment(true);
        const latest = sessions[sessions.length - 1];
        setHasInProgress(latest.status === 'in_progress');
        if (latest.status === 'completed' && latest.risk_results?.length > 0) {
          const risk = latest.risk_results[latest.risk_results.length - 1];
          if (risk.overall) setRiskLevel(risk.overall);
        }
      }
      if (readings.length > 0) {
        const nonHba1c = readings.filter((r: any) => r.reading_type !== 'hba1c');
        const chosen = nonHba1c.length > 0
          ? nonHba1c[nonHba1c.length - 1]
          : readings[readings.length - 1];
        setLastSugar(`${chosen.value}${chosen.reading_type === 'hba1c' ? '%' : ' mg/dL'}`);
      } else {
        const completed = sessions.filter((s: any) => s.status === 'completed');
        if (completed.length > 0) {
          const responses = completed[completed.length - 1].responses || [];
          let found: { value: number; unit: string } | null = null;
          for (const r of responses) {
            if (r.question_id === 'fasting_sugar') {
              const v = parseFloat(r.answer_value);
              if (!isNaN(v)) found = { value: v, unit: ' mg/dL' };
            }
          }
          if (!found) {
            for (const r of responses) {
              if (r.question_id === 'hba1c') {
                const v = parseFloat(r.answer_value);
                if (!isNaN(v)) found = { value: v, unit: '%' };
              }
            }
          }
          if (found) setLastSugar(`${found.value}${found.unit}`);
        }
      }
      const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
      const weekLogs = logs.filter((l: any) => new Date(l.activity_date) >= weekAgo);
      const total = weekLogs.reduce((sum: number, l: any) => sum + (l.completed_minutes || 0), 0);
      setActiveMinutes(total);

      if (fu) setFollowUp(fu);
      if (adh) setAdherenceStreak(adh.adherence_streak_weeks || 0);
    }).catch(() => {});
  }, [user]);

  const followUpStatus = (() => {
    if (!followUp) return null;
    if (followUp.status === 'due' || followUp.status === 'overdue') {
      return { icon: <AlertCircle size={24} />, color: followUp.status === 'overdue' ? '#EF4444' : '#F59E0B', title: t.followUpOverdue || 'Check-In Overdue' };
    }
    return { icon: <CheckCircle size={24} />, color: '#10B981', title: t.followUpCompleted || 'Check-In Completed' };
  })();

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
            {t.notifPrompt || 'Allow Notifications to get follow up alerts and reminders'}
            <span style={{ display: 'block', fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>
              {t.notifChangeSettings || 'You can change this anytime in Settings.'}
            </span>
          </span>
          <button className="btn-primary" onClick={() => {
            setDismissNotifBanner(true);
            sessionStorage.setItem('df_notif_dismissed', '1');
            if (user) subscribeToPush(user.id);
          }} style={{ padding: '3px 10px', fontSize: 11, whiteSpace: 'nowrap', width: 'auto' }}>
            {t.reminderEnable || 'Allow'}
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
        {followUpStatus && (
          <StatusCard
            icon={followUpStatus.icon}
            title={t.followUp || 'Check-In'}
            value={followUpStatus.title}
            color={followUpStatus.color}
          />
        )}
        <StatusCard
          icon={<Zap size={24} />}
          title={t.riskCategory}
          value={riskLevel || (isComplete ? 'Low' : '--')}
          color="#8B5CF6"
        />
      </div>

      <div className="action-cards">
        {!hasAssessment ? (
          <ActionCard
            icon={<ClipboardList size={24} />}
            title={t.startAssessment}
            description={t.descAssessment || "Complete the initial assessment to get your personalized plan"}
            onClick={() => navigate('/assessment')}
            color="#2C6E49"
          />
        ) : hasInProgress ? (
          <ActionCard
            icon={<ClipboardList size={24} />}
            title={t.resumeAssessment}
            description={t.descResume || "Continue your assessment"}
            onClick={() => navigate('/assessment')}
            color="#F59E0B"
          />
        ) : (
          <ActionCard
            icon={<FileText size={24} />}
            title={t.viewPlan}
            description={t.descPlan || "View your exercise plan"}
            onClick={() => navigate('/prescription/latest')}
            color="#2C6E49"
          />
        )}

        <ActionCard
          icon={<Activity size={24} />}
          title={t.logActivity}
          description={t.descActivity || "Log weekly physical activity"}
          onClick={() => navigate('/activity')}
          color="#3B82F6"
        />

        <ActionCard
          icon={<Droplets size={24} />}
          title={t.addSugarReading}
          description={t.descSugar || "Record your blood sugar level"}
          onClick={() => navigate('/sugar')}
          color="#F59E0B"
        />

        <ActionCard
          icon={<Shield size={24} />}
          title={t.followUp || 'Weekly Check-In'}
          description={followUpStatus ? followUpStatus.title : (t.followUp || 'Check-In')}
          onClick={() => navigate('/follow-up')}
          color="#8B5CF6"
        />
      </div>

      <div className="home-footer">
        <p className="disclaimer">{t.disclaimer || "DiaFit Coach v2.0 — Not a substitute for medical advice."}</p>
      </div>
    </div>
  );
}
