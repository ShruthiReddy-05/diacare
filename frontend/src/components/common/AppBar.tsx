import LanguageToggle from './LanguageToggle';
import { useUserStore } from '../../stores/useUserStore';
import { translations } from '../../data/translations';

interface Props {
  title?: string;
  showBack?: boolean;
  onBack?: () => void;
  rightAction?: React.ReactNode;
}

export default function AppBar({ title, showBack, onBack, rightAction }: Props) {
  const { language } = useUserStore();
  const t = translations[language];

  return (
    <header className="app-bar">
      <div className="app-bar-inner">
        <div className="app-bar-left">
          {showBack ? (
            <button className="icon-btn" onClick={onBack} aria-label="Back">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
          ) : (
            <img src="/diacare_logo_clean.png" alt="DiaCare Logo" className="app-bar-logo" />
          )}
          <h1 className="app-bar-title">{title || t.appTitle}</h1>
        </div>
        <div className="app-bar-right">
          {rightAction}
          <LanguageToggle />
        </div>
      </div>
    </header>
  );
}
