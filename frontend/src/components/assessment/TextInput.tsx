import { useRef, useEffect } from 'react';

interface Props {
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  onSubmit?: () => void;
}

export default function TextInput({ value, onChange, placeholder, onSubmit }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && value?.trim() && onSubmit) {
      onSubmit();
    }
  };

  return (
    <div className="text-input-wrap">
      <input
        ref={inputRef}
        className="form-input text-input-chat"
        type="text"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || 'Type your answer...'}
      />
      {value?.trim() && onSubmit && (
        <button className="btn-primary btn-send" onClick={onSubmit}>
          Submit
        </button>
      )}
    </div>
  );
}
