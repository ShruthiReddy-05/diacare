import { useEffect, useState, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { AlertTriangle, RefreshCcw } from 'lucide-react';
import { useUserStore } from '../../stores/useUserStore';
import { useSafetyLockStore } from '../../stores/useSafetyLockStore';
import { translations } from '../../data/translations';
import api from '../../services/api/client';
import LanguageToggle from '../common/LanguageToggle';

// Module D halt, enforced by the server: while /api/safety/.../status (or any
// 423 response) says the patient is locked, every patient screen is replaced
// by the emergency script. The script text is shown exactly as the server
// sends it. Only a clinician acknowledging the event on the dashboard unlocks.
export default function SafetyLockGate({ children }: { children: ReactNode }) {
  const { user } = useUserStore();
  const { lock, setLock } = useSafetyLockStore();
  const { pathname } = useLocation();
  const isAdminRoute = pathname.startsWith('/admin');

  useEffect(() => {
    if (!user || isAdminRoute) return;
    api.getSafetyStatus(user.id).then(setLock).catch(() => { /* keep last known lock */ });
  }, [user?.id, pathname]);

  if (!user || isAdminRoute || !lock) return <>{children}</>;
  return <EmergencyScriptScreen />;
}

function EmergencyScriptScreen() {
  const { user, language } = useUserStore();
  const { lock, setLock } = useSafetyLockStore();
  const [checking, setChecking] = useState(false);
  const t = translations[language];

  const refresh = async () => {
    if (!user) return;
    setChecking(true);
    try {
      setLock(await api.getSafetyStatus(user.id));
    } catch { /* stay locked */ } finally {
      setChecking(false);
    }
  };

  // The script language follows the patient's server-side preference, so
  // persist a language switch before re-fetching the script.
  useEffect(() => {
    if (!user || !lock || lock.language === language) return;
    api.updateLanguage(user.id, language).then(refresh).catch(() => { });
  }, [language]);

  if (!lock) return null;

  return (
    <div className="page-container">
      <main
        className="page-content"
        role="alert"
        style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 24, textAlign: 'center', paddingTop: 60 }}
      >
        <LanguageToggle />
        <AlertTriangle size={72} color="var(--error)" />
        <p lang={lock.language} style={{ fontSize: 20, lineHeight: 1.6, fontWeight: 600, maxWidth: 420 }}>
          {lock.emergency_script}
        </p>
        <button className="btn-secondary" onClick={refresh} disabled={checking} style={{ marginTop: 16 }}>
          <RefreshCcw size={18} /> {checking ? '...' : t.safetyLockRecheck}
        </button>
      </main>
    </div>
  );
}
