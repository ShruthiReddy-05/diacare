import type { ReactNode } from 'react';
import { motion } from 'framer-motion';

interface Props {
  icon: ReactNode;
  title: string;
  value: string | ReactNode;
  color?: string;
}

export default function StatusCard({ icon, title, value, color }: Props) {
  return (
    <motion.div
      className="status-card"
      whileHover={{ scale: 1.02 }}
      transition={{ type: 'spring', stiffness: 300 }}
    >
      <div className="status-card-icon" style={{ color }}>
        {icon}
      </div>
      <div className="status-card-body">
        <p className="status-card-title">{title}</p>
        <p className="status-card-value">{value}</p>
      </div>
    </motion.div>
  );
}
