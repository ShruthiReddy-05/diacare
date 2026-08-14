import { useState } from 'react';

interface Props {
  onChange: (value: string) => void;
  onSubmit?: () => void;
}

export default function BloodPressureInput({ onChange, onSubmit }: Props) {
  const [systolic, setSystolic] = useState('');
  const [diastolic, setDiastolic] = useState('');

  const handleChange = (field: 'systolic' | 'diastolic', val: string) => {
    const clean = val.replace(/[^0-9]/g, '').slice(0, 3);
    if (field === 'systolic') {
      setSystolic(clean);
    } else {
      setDiastolic(clean);
    }
    const sys = field === 'systolic' ? clean : systolic;
    const dia = field === 'diastolic' ? clean : diastolic;
    if (sys && dia) {
      onChange(`${sys}/${dia}`);
    }
  };

  const bothFilled = systolic.length > 0 && diastolic.length > 0;

  return (
    <div className="hw-input-wrap">
      <div className="hw-field">
        <label className="form-label">Systolic (top number)</label>
        <input
          className="form-input"
          type="text"
          inputMode="numeric"
          value={systolic}
          onChange={(e) => handleChange('systolic', e.target.value)}
          placeholder="120"
        />
      </div>
      <span className="bp-slash" aria-hidden="true">/</span>
      <div className="hw-field">
        <label className="form-label">Diastolic (bottom number)</label>
        <input
          className="form-input"
          type="text"
          inputMode="numeric"
          value={diastolic}
          onChange={(e) => handleChange('diastolic', e.target.value)}
          placeholder="80"
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
