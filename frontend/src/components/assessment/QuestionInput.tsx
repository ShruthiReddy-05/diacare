import type { QuestionDefinition, LanguageCode } from '../../domain/types';
import OptionButtons from './OptionButtons';
import NumberInput from './NumberInput';
import ScaleInput from './ScaleInput';
import TextInput from './TextInput';
import HeightWeightInput from './HeightWeightInput';
import DateInput from './DateInput';

const DEFAULT_YES_NO = [
  { value: 'yes', label: { en: 'Yes', ta: 'ஆம்' } },
  { value: 'no', label: { en: 'No', ta: 'இல்லை' } },
];

interface Props {
  question: QuestionDefinition;
  value: any;
  onChange: (value: any) => void;
  language: LanguageCode;
  selectedValues?: string[];
  onSubmit?: (value?: any) => void;
}

export default function QuestionInput({ question, value, onChange, language, selectedValues, onSubmit }: Props) {
  switch (question.inputType) {
    case 'single_choice':
    case 'confirmation':
      return (
        <OptionButtons
          options={question.options || (question.inputType === 'confirmation' ? DEFAULT_YES_NO : [])}
          selected={value}
          onSelect={(optValue) => {
            onChange(optValue);
            if (onSubmit) onSubmit(optValue);
          }}
          language={language}
        />
      );

    case 'multi_choice':
      return (
        <OptionButtons
          options={question.options || []}
          onSelect={(optValue: string) => {
            const current = selectedValues || [];
            const next = current.includes(optValue)
              ? current.filter((v: string) => v !== optValue)
              : [...current, optValue];
            onChange(next);
          }}
          language={language}
          multi
          selectedValues={selectedValues || []}
          onSubmit={() => onSubmit?.()}
        />
      );

    case 'number':
      return (
        <NumberInput
          value={value}
          onChange={onChange}
          min={question.min}
          max={question.max}
          unit={question.unit}
          onSubmit={() => onSubmit?.()}
        />
      );

    case 'decimal':
      return (
        <NumberInput
          value={value}
          onChange={onChange}
          min={question.min}
          max={question.max}
          unit={question.unit}
          decimal
          onSubmit={() => onSubmit?.()}
        />
      );

    case 'scale':
      return (
        <ScaleInput
          min={question.min || 1}
          max={question.max || 5}
          value={value}
          onChange={onChange}
          onSubmit={(n) => onSubmit?.(n)}
        />
      );

    case 'text':
      return (
        <TextInput
          value={value}
          onChange={onChange}
          onSubmit={() => onSubmit?.()}
        />
      );

    case 'height_weight':
      return <HeightWeightInput onChange={onChange} onSubmit={() => onSubmit?.()} />;

    case 'date':
      return (
        <DateInput
          value={value}
          onChange={onChange}
          onSubmit={() => onSubmit?.()}
        />
      );

    default:
      return null;
  }
}
