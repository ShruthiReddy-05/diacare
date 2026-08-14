import { useState } from 'react';

interface Props {
  onChange: (value: string) => void;
  onSubmit?: () => void;
}

export default function BloodSugarTargetInput({ onChange, onSubmit }: Props) {
  const [fasting, setFasting] = useState('');
  const [postMeal, setPostMeal] = useState('');

  const handleChange = (field: 'fasting' | 'postMeal', val: string) => {
    const clean = val.replace(/[^0-9]/g, '').slice(0, 3);
    if (field === 'fasting') {
      setFasting(clean);
    } else {
      setPostMeal(clean);
    }
    const f = field === 'fasting' ? clean : fasting;
    const p = field === 'postMeal' ? clean : postMeal;
    if (f && p) {
      onChange(`${f}/${p}`);
    }
  };

  const bothFilled = fasting.length > 0 && postMeal.length > 0;

  return (
    <div className="hw-input-wrap">
      <div className="hw-field">
        <label className="form-label">Fasting target (mg/dl)</label>
        <input
          className="form-input"
          type="text"
          inputMode="numeric"
          value={fasting}
          onChange={(e) => handleChange('fasting', e.target.value)}
          placeholder="100"
        />
      </div>
      <span className="bp-slash" aria-hidden="true">/</span>
      <div className="hw-field">
        <label className="form-label">Post-meal target (mg/dl)</label>
        <input
          className="form-input"
          type="text"
          inputMode="numeric"
          value={postMeal}
          onChange={(e) => handleChange('postMeal', e.target.value)}
          placeholder="130"
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
