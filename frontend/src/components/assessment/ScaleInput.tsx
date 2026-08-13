import { motion } from 'framer-motion';

interface Props {
  min: number;
  max: number;
  value?: number;
  onChange: (value: number) => void;
  onSubmit?: (value: number) => void;
}

export default function ScaleInput({ min, max, value, onChange, onSubmit }: Props) {
  const steps: number[] = [];
  for (let i = min; i <= max; i++) steps.push(i);

  const handleSelect = (n: number) => {
    onChange(n);
    if (onSubmit) onSubmit(n);
  };

  return (
    <div className="scale-input-wrap">
      <div className="scale-bar">
        {steps.map((n) => (
          <motion.button
            key={n}
            className={`scale-dot ${value !== undefined && n <= value ? 'active' : ''}`}
            whileTap={{ scale: 1.2 }}
            onClick={() => handleSelect(n)}
          >
            <span className="scale-label">{n}</span>
          </motion.button>
        ))}
      </div>
      <div className="scale-labels">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}
