import { motion } from 'framer-motion';

interface Props {
  answered: number;
  total: number;
  moduleTitle?: string;
}

export default function ProgressBar({ answered, total, moduleTitle }: Props) {
  const pct = total > 0 ? Math.round((answered / total) * 100) : 0;

  return (
    <div className="progress-section">
      {moduleTitle && <p className="module-label">{moduleTitle}</p>}
      <div className="progress-track">
        <motion.div
          className="progress-fill"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      </div>
      <span className="progress-pct">{answered}/{total}</span>
    </div>
  );
}
