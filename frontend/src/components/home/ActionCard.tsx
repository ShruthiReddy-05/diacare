import { motion } from 'framer-motion';
import { ChevronRight } from 'lucide-react';

interface Props {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  onClick: () => void;
  color?: string;
}

export default function ActionCard({ title, description, icon, onClick, color }: Props) {
  return (
    <motion.button
      className="action-card"
      onClick={onClick}
      whileTap={{ scale: 0.98 }}
    >
      {icon && <div className="action-card-icon" style={{ color }}>{icon}</div>}
      <div className="action-card-body">
        <p className="action-card-title">{title}</p>
        {description && <p className="action-card-desc">{description}</p>}
      </div>
      <ChevronRight size={20} className="action-chevron" />
    </motion.button>
  );
}
