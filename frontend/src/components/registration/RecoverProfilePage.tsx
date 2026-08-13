import { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useUserStore } from '../../stores/useUserStore';
import { translations } from '../../data/translations';
import { ArrowLeft, RotateCcw } from 'lucide-react';

export default function RecoverProfilePage() {
  const navigate = useNavigate();
  const { language, recover } = useUserStore();
  const t = translations[language];
  const [displayUserId, setDisplayUserId] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRecover = async () => {
    if (!displayUserId.trim() || !firstName.trim() || !lastName.trim()) {
      setError(t.enterDetails);
      return;
    }
    setError('');
    setLoading(true);
    try {
      await recover(displayUserId.trim(), firstName.trim(), lastName.trim());
      navigate('/home');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="landing-container">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="landing-card">
        <button className="icon-btn back-btn" onClick={() => navigate('/')}>
          <ArrowLeft size={24} />
        </button>

        <div className="logo-area">
          <RotateCcw size={40} className="logo-icon" />
          <h1>{t.recoverProfile}</h1>
          <p className="tagline">{t.recoveryDesc}</p>
        </div>

        <div className="form-group">
          <label className="form-label">{t.saveThisId}</label>
          <input
            className="form-input"
            value={displayUserId}
            onChange={(e) => setDisplayUserId(e.target.value)}
            placeholder="e.g. johnsmi42"
          />
        </div>
        <div className="form-group">
          <label className="form-label">{t.firstName}</label>
          <input
            className="form-input"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            placeholder={t.firstName}
          />
        </div>
        <div className="form-group">
          <label className="form-label">{t.lastName}</label>
          <input
            className="form-input"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            placeholder={t.lastName}
          />
        </div>

        {error && <p className="form-error">{error}</p>}

        <button className="btn-primary" onClick={handleRecover} disabled={loading}>
          {loading ? '...' : t.recoverProfile}
        </button>

        <p className="recover-link-text">
          {t.notRegistered}
          <button className="link-btn" onClick={() => navigate('/')}>
            {t.register}
          </button>
        </p>
      </motion.div>
    </div>
  );
}
