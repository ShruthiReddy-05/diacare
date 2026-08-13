import { useState, useRef, useEffect } from 'react';

interface Props {
  value?: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  unit?: string;
  decimal?: boolean;
  onSubmit?: () => void;
}

export default function NumberInput({ value, onChange, min, max, unit, decimal, onSubmit }: Props) {
  const [str, setStr] = useState(value !== undefined ? String(value) : '');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/[^0-9.]/g, '');
    setStr(raw);
    const num = decimal ? parseFloat(raw) : parseInt(raw, 10);
    if (!isNaN(num)) onChange(num);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && str.trim() && onSubmit) {
      onSubmit();
    }
  };

  const hasValue = str.trim().length > 0 && !isNaN(decimal ? parseFloat(str) : parseInt(str, 10));

  return (
    <div className="number-input-wrap">
      <div className="number-input-row">
        <input
          ref={inputRef}
          className="number-input"
          type="text"
          inputMode="decimal"
          value={str}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={min !== undefined ? String(min) : '0'}
          min={min}
          max={max}
        />
        {unit && <span className="input-unit">{unit}</span>}
      </div>
      {min !== undefined && max !== undefined && (
        <div className="range-hint">{min} – {max}</div>
      )}
      {hasValue && onSubmit && (
        <button className="btn-primary btn-send" onClick={onSubmit}>
          Submit
        </button>
      )}
    </div>
  );
}
