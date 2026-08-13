import { motion } from 'framer-motion';
import type { OptionDefinition } from '../../domain/types';

interface Props {
  options: OptionDefinition[];
  selected?: string;
  onSelect: (value: string) => void;
  language: 'en' | 'ta';
  multi?: boolean;
  selectedValues?: string[];
  onSubmit?: () => void;
  submitLabel?: string;
}

export default function OptionButtons({ options, selected, onSelect, language, multi, selectedValues = [], onSubmit, submitLabel }: Props) {
  if (multi) {
    return (
      <div className="options-wrapper">
        <div className="options-grid two-col">
          {options.map((opt) => {
            const isActive = selectedValues.includes(opt.value);
            return (
              <motion.button
                key={opt.value}
                className={`option-btn ${isActive ? 'active' : ''}`}
                whileTap={{ scale: 0.97 }}
                onClick={() => onSelect(opt.value)}
              >
                <span className={`option-check ${isActive ? 'checked' : ''}`}>
                  {isActive && <span>✓</span>}
                </span>
                <span>{opt.label[language]}</span>
              </motion.button>
            );
          })}
        </div>
        {selectedValues.length > 0 && onSubmit && (
          <motion.button
            className="btn-primary btn-done"
            whileTap={{ scale: 0.95 }}
            onClick={onSubmit}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {submitLabel || `Done (${selectedValues.length})`}
          </motion.button>
        )}
      </div>
    );
  }

  return (
    <div className="options-wrapper">
      <div className="options-grid two-col">
        {options.map((opt) => (
          <motion.button
            key={opt.value}
            className={`option-btn ${selected === opt.value ? 'active' : ''}`}
            whileTap={{ scale: 0.97 }}
            onClick={() => onSelect(opt.value)}
          >
            {opt.label[language]}
          </motion.button>
        ))}
      </div>
    </div>
  );
}
