import { motion } from 'framer-motion';

interface LoadingSpinnerProps {
  text?: string;
  showLogo?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export default function LoadingSpinner({ text, showLogo = true, size = 'md' }: LoadingSpinnerProps) {
  return (
    <div className={`loading-spinner size-${size}`}>
      {showLogo && (
        <motion.div
          className="loading-logo-box"
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: [0.95, 1.05, 0.95] }}
          transition={{
            opacity: { duration: 0.3 },
            scale: { repeat: Infinity, duration: 2.2, ease: 'easeInOut' },
          }}
        >
          <div className="loading-logo-glow" />
          <img
            src="/diafit_logo.jpeg"
            alt="DiaFit Logo"
            className="loading-logo-img"
          />
        </motion.div>
      )}

      <motion.div
        className="spinner-ring"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }}
      >
        <div className="spinner-circle" />
      </motion.div>
      {text && <p className="spinner-text">{text}</p>}
    </div>
  );
}
