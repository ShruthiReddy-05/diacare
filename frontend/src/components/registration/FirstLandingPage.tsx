import { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useUserStore } from '../../stores/useUserStore';
import { translations } from '../../data/translations';
import LanguageToggle from '../common/LanguageToggle';

export default function FirstLandingPage() {
  const navigate = useNavigate();
  const { language, register, isLoading } = useUserStore();
  const t = translations[language];
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [savedId, setSavedId] = useState<string | null>(null);
  const [error, setError] = useState('');

  const handleRegister = async () => {
    if (!firstName.trim() || !lastName.trim()) {
      setError(t.enterDetails);
      return;
    }
    setError('');
    try {
      const profile = await register(firstName.trim(), lastName.trim(), language);
      setSavedId(profile.display_user_id);
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (savedId) {
    return (
      <div className="landing-container">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="landing-card">
          <div className="logo-area">
            <img src="/diacare_logo_clean.png" alt="DiaCare Logo" className="app-main-logo" />
            <h1>{t.appTitle}</h1>
          </div>
          <div className="recovery-id-box">
            <p className="save-id-label">{t.saveThisId}</p>
            <p className="display-id">{savedId}</p>
            <p className="save-id-hint">{t.recoveryDesc}</p>
          </div>
          <button className="btn-primary" onClick={() => navigate('/home')}>
            {t.continueBtn}
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="landing-container">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="landing-card">
        <div className="logo-area">
          <div className="logo-icon-wrapper brand-logo-wrapper">
            <img src="/diacare_logo_clean.png" alt="DiaCare Logo" className="app-main-logo" />
          </div>
          <h1 className="app-title">{t.appTitle}</h1>
          <p className="tagline">{t.tagline}</p>
        </div>

        <div className="lang-select-area">
          <LanguageToggle />
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

        <button className="btn-primary" onClick={handleRegister} disabled={isLoading}>
          {isLoading ? '...' : t.register}
        </button>

        <p className="recover-link-text">
          {t.recoverLink}
          <button className="link-btn" onClick={() => navigate('/recover')}>
            {t.recoverProfile}
          </button>
        </p>
      </motion.div>
    </div>
  );
}
