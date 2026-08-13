import { motion } from 'framer-motion';
import { useUserStore } from '../../stores/useUserStore';
import type { LanguageCode } from '../../domain/types';

const languages: { code: LanguageCode; label: string }[] = [
  { code: 'en', label: 'EN' },
  { code: 'ta', label: 'தமிழ்' },
];

export default function LanguageToggle() {
  const { language, setLanguage } = useUserStore();

  return (
    <div className="lang-toggle">
      {languages.map((l) => (
        <button
          key={l.code}
          className={`lang-btn ${language === l.code ? 'active' : ''}`}
          onClick={() => setLanguage(l.code)}
        >
          {language === l.code && (
            <motion.div
              layoutId="lang-bg"
              className="lang-bg-indicator"
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            />
          )}
          <span className="lang-label">{l.label}</span>
        </button>
      ))}
    </div>
  );
}
