import { useRef, useEffect } from 'react';

interface Props {
  value?: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
}

export default function DateInput({ value, onChange, onSubmit }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div className="text-input-wrap">
      <input
        ref={inputRef}
        className="form-input text-input-chat"
        type="date"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        max={new Date().toISOString().slice(0, 10)}
      />
      {value && onSubmit && (
        <button className="btn-primary btn-send" onClick={onSubmit}>
          Submit
        </button>
      )}
    </div>
  );
}
