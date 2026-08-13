import { useNavigate, useLocation } from 'react-router-dom';
import { useUserStore } from '../../stores/useUserStore';
import { translations } from '../../data/translations';
import { Home, ClipboardList, BarChart3, Settings } from 'lucide-react';

const navItems = [
  { path: '/home', icon: Home, labelKey: 'home' as const },
  { path: '/assessment', icon: ClipboardList, labelKey: 'assessment' as const },
  { path: '/history', icon: BarChart3, labelKey: 'history' as const },
  { path: '/settings', icon: Settings, labelKey: 'settings' as const },
];

export default function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const { language } = useUserStore();
  const t = translations[language];

  return (
    <nav className="bottom-nav">
      {navItems.map(({ path, icon: Icon, labelKey }) => {
        const isActive = location.pathname.startsWith(path);
        return (
          <button
            key={path}
            className={`nav-item ${isActive ? 'active' : ''}`}
            onClick={() => navigate(path)}
          >
            <Icon size={22} />
            <span className="nav-label">{t[labelKey]}</span>
          </button>
        );
      })}
    </nav>
  );
}
