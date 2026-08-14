import type { QuestionDefinition, LanguageCode } from '../domain/types';

const WORD_TO_NUM: Record<string, number> = {
  zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5,
  six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15,
  sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20,
  thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70,
  eighty: 80, ninety: 90, hundred: 100,
};

const TA_WORD_TO_NUM: Record<string, number> = {
  பூஜ்யம்: 0, ஒன்று: 1, இரண்டு: 2, மூன்று: 3, நான்கு: 4,
  ஐந்து: 5, ஆறு: 6, ஏழு: 7, எட்டு: 8, ஒன்பது: 9,
  பத்து: 10, பதினொன்று: 11, பன்னிரண்டு: 12, பதின்மூன்று: 13,
  பதினான்கு: 14, பதினைந்து: 15, பதினாறு: 16, பதினேழு: 17,
  பதினெட்டு: 18, பத்தொன்பது: 19, இருபது: 20,
  முப்பது: 30, நாற்பது: 40, ஐம்பது: 50, அறுபது: 60,
  எழுபது: 70, எண்பது: 80, தொண்ணூறு: 90, நூறு: 100,
};

function extractNumber(text: string): number | null {
  const cleaned = text.toLowerCase().replace(/[^a-z0-9\u0B80-\u0BFF.\s]/g, ' ').trim();

  const nums = cleaned.match(/\d+(?:\.\d+)?/g);
  if (nums && nums.length > 0) {
    const first = parseFloat(nums[0]);
    if (!isNaN(first)) return first;
  }

  const words = cleaned.split(/\s+/);
  for (let w of words) {
    w = w.replace(/[.,!?;:]+$/, '');
    if (!w) continue;
    if (w === 'a' || w === 'an') return 1;
    if (w in WORD_TO_NUM) return WORD_TO_NUM[w];
    if (w in TA_WORD_TO_NUM) return TA_WORD_TO_NUM[w];
  }

  for (let w of words) {
    w = w.replace(/[.,!?;:]+$/, '');
    if (w === 'half' || w === 'அரை') return 0.5;
  }

  return null;
}

function matchTranscriptToLabel(transcript: string, optionLabel: string): boolean {
  const t = transcript.toLowerCase().trim();
  const l = optionLabel.toLowerCase().trim();

  if (t === l) return true;
  if (t.includes(l)) return true;

  const tWords = t.split(/\s+/);
  const lWords = l.split(/\s+/);
  const matchCount = lWords.filter(w => w.length > 2 && tWords.includes(w)).length;
  if (matchCount > 0 && matchCount >= lWords.filter(w => w.length > 2).length / 2) return true;

  return false;
}

export function matchVoiceTranscript(
  transcript: string,
  question: QuestionDefinition,
  language: LanguageCode
): any {
  if (!transcript || typeof transcript !== 'string') return transcript;
  const trimmed = transcript.trim();
  if (!trimmed) return transcript;

  const { inputType } = question;
  const options = question.options || (inputType === 'confirmation'
    ? [{ value: 'yes', label: { en: 'Yes', ta: 'ஆம்' } }, { value: 'no', label: { en: 'No', ta: 'இல்லை' } }]
    : undefined);

  if (inputType === 'single_choice' || inputType === 'confirmation') {
    if (!options) return trimmed;

    const firstWord = trimmed.split(/\s+/)[0].toLowerCase();

    const directValue = options.find(o => o.value.toLowerCase() === trimmed.toLowerCase());
    if (directValue) return directValue.value;

    const firstWordValue = options.find(o => o.value.toLowerCase() === firstWord);
    if (firstWordValue) return firstWordValue.value;

    for (const opt of options) {
      if (matchTranscriptToLabel(trimmed, opt.label.en)) return opt.value;
      if (language === 'ta' && matchTranscriptToLabel(trimmed, opt.label.ta)) return opt.value;
    }

    if (options.length === 2 && options.some(o => o.value === 'yes')) {
      if (/^(yeah|yep|sure|ok|okay|begin|start|show|go\s*ahead)/i.test(trimmed)) return 'yes';
      if (/^(nah|nope|not|never|stop|skip)/i.test(trimmed)) return 'no';
      if (language === 'ta') {
        if (/^(ஆம்|சரி|தொடங்கலாம்|காட்டு|பார்க்க)/i.test(trimmed)) return 'yes';
        if (/^(இல்லை|வேண்டாம்|பிறகு)/i.test(trimmed)) return 'no';
      }
    }

    return trimmed;
  }

  if (inputType === 'multi_choice') {
    if (!options) return [trimmed];

    const parts = trimmed.split(/[\s,]+(?:and[\s,]+)?/).filter(Boolean);
    const matched: string[] = [];

    for (const part of parts) {
      const p = part.toLowerCase();
      const direct = options.find(o => o.value.toLowerCase() === p);
      if (direct) { matched.push(direct.value); continue; }
      const byEn = options.find(o => o.label.en.toLowerCase().includes(p));
      if (byEn) { matched.push(byEn.value); continue; }
      if (language === 'ta') {
        const byTa = options.find(o => o.label.ta.toLowerCase().includes(p));
        if (byTa) { matched.push(byTa.value); continue; }
      }
    }

    return matched.length > 0 ? [...new Set(matched)] : [trimmed];
  }

  if (inputType === 'height_weight') {
    const heightMatch = trimmed.match(/(\d+(?:\.\d+)?)\s*(?:cm|centimeter|centimetre)/i);
    const weightMatch = trimmed.match(/(\d+(?:\.\d+)?)\s*(?:kg|kilo|kilogram|kilograms)/i);

    if (heightMatch || weightMatch) {
      const heightCm = heightMatch ? parseFloat(heightMatch[1]) : 0;
      const weightKg = weightMatch ? parseFloat(weightMatch[1]) : 0;
      if (heightCm > 0 && weightKg > 0) return { heightCm, weightKg };
    }

    const allNums = trimmed.match(/\d+(?:\.\d+)?/g);
    if (allNums && allNums.length >= 2) {
      const nums = allNums.map(Number).filter(n => n >= 30 && n <= 300);
      if (nums.length >= 2) {
        const heightCandidates = nums.filter(n => n >= 100 && n <= 300);
        const weightCandidates = nums.filter(n => n >= 30 && n < 300);
        const heightCm = heightCandidates[0] || nums[0];
        const weightKg = weightCandidates.find(w => w !== heightCm) || nums.find(n => n !== heightCm) || nums[1];
        return { heightCm, weightKg };
      }
      if (nums.length === 2) {
        const sorted = [...nums].sort((a, b) => b - a);
        return { heightCm: sorted[0], weightKg: sorted[1] };
      }
    }

    const num = extractNumber(trimmed);
    if (num !== null) {
      return { heightCm: 170, weightKg: num };
    }

    return trimmed;
  }

  if (inputType === 'number' || inputType === 'decimal' || inputType === 'scale') {
    const num = extractNumber(trimmed);
    if (num !== null) {
      if (question.min !== undefined && num < question.min) return trimmed;
      if (question.max !== undefined && num > question.max) return trimmed;
      return num;
    }
    return trimmed;
  }

  return trimmed;
}
