import { useState } from 'react';

interface Props {
  onChange: (value: { heightCm: number; weightKg: number }) => void;
  onSubmit?: () => void;
}

export default function HeightWeightInput({ onChange, onSubmit }: Props) {
  const [height, setHeight] = useState('');
  const [weight, setWeight] = useState('');

  const handleChange = (field: 'height' | 'weight', val: string) => {
    const clean = val.replace(/[^0-9.]/g, '');
    if (field === 'height') {
      setHeight(clean);
    } else {
      setWeight(clean);
    }
    const h = parseFloat(field === 'height' ? clean : height);
    const w = parseFloat(field === 'weight' ? clean : weight);
    if (!isNaN(h) && !isNaN(w) && h > 0 && w > 0) {
      onChange({ heightCm: h, weightKg: w });
    }
  };

  const h = parseFloat(height);
  const w = parseFloat(weight);
  const bothFilled = !isNaN(h) && h > 0 && !isNaN(w) && w > 0;

  return (
    <div className="hw-input-wrap">
      <div className="hw-field">
        <label className="form-label">Height (cm)</label>
        <input
          className="form-input"
          type="text"
          inputMode="decimal"
          value={height}
          onChange={(e) => handleChange('height', e.target.value)}
          placeholder="170"
        />
      </div>
      <div className="hw-field">
        <label className="form-label">Weight (kg)</label>
        <input
          className="form-input"
          type="text"
          inputMode="decimal"
          value={weight}
          onChange={(e) => handleChange('weight', e.target.value)}
          placeholder="70"
        />
      </div>
      {bothFilled && onSubmit && (
        <button className="btn-primary btn-send" onClick={onSubmit}>
          Submit
        </button>
      )}
    </div>
  );
}
