import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useUserStore } from '../stores/useUserStore';
import { translations } from '../data/translations';
import api from '../services/api/client';
import AppBar from '../components/common/AppBar';
import BottomNav from '../components/common/BottomNav';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { BarChart3, ChevronDown, ChevronUp, CheckCircle, AlertCircle } from 'lucide-react';

function stripHtml(html: string): string {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  return doc.body.textContent || '';
}

function formatAnswer(r: any): string {
  if (r.question_id === 'height_weight' && typeof r.answer_value === 'string') {
    const parts = r.answer_value.replace(/cm|kg/g, '').split(',');
    if (parts.length >= 2 && parts[0].trim() && parts[1].trim()) {
      return `Height: ${parts[0].trim()} cm, Weight: ${parts[1].trim()} kg`;
    }
  }
  return r.answer_value;
}

export default function History() {
  const navigate = useNavigate();
  const { language, user } = useUserStore();
  const t = translations[language];
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (!user) { navigate('/'); return; }
    api.getUserConversationSessions(user.id).then((data) => {
      setSessions(data || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [user]);

  return (
    <div className="page-container">
      <AppBar title={t.history} />
      <main className="page-content">
        {loading && <LoadingSpinner />}

        {!loading && sessions.length === 0 && (
          <motion.div
            className="empty-state"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <BarChart3 size={48} className="empty-icon" />
            <p>{t.noHistory}</p>
          </motion.div>
        )}

        <div className="history-list">
          <AnimatePresence>
            {sessions.map((s: any) => (
              <motion.div
                key={s.id}
                className="history-card"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <button
                  className="history-card-header"
                  onClick={() => setExpanded(expanded === s.id ? null : s.id)}
                >
                  <div className="history-card-info">
                    <span className="history-date">
                      {t.assessmentOn} {new Date(s.started_at || s.created_at).toLocaleString()}
                    </span>
                    <span className={`history-status ${s.status}`}>
                      {s.status === 'completed' ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
                      {s.status === 'completed' ? t.completed : t.inProgress}
                    </span>
                  </div>
                  {expanded === s.id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </button>

                <AnimatePresence>
                  {expanded === s.id && (
                    <motion.div
                      className="history-card-body"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                    >
                      {s.responses?.map((r: any, i: number) => (
                        <div key={i} className="history-response">
                          <p className="history-q">{stripHtml(r.question_text_en || r.question_id)}</p>
                          <p className="history-a">{formatAnswer(r)}</p>
                        </div>
                      ))}
                      {(!s.responses || s.responses.length === 0) && (
                        <p className="history-empty">No responses recorded.</p>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </main>
      <BottomNav />
    </div>
  );
}
