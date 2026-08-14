import type { ConversationScript, QuestionDefinition } from './types';

// The backend script JSON uses snake_case (input_type, save_as) since it's
// authored/consumed by Python; this is the one place that maps it to the
// camelCase QuestionDefinition shape the rest of the frontend expects.
export function parseScript(raw: any): ConversationScript {
  return {
    id: raw.id,
    version: raw.version,
    status: raw.status,
    title: raw.title,
    modules: (raw.modules || []).map((m: any) => ({
      id: m.id,
      title: m.title,
      sitting: m.sitting,
      questions: (m.questions || []).map((q: any) => ({
        id: q.id,
        moduleId: m.id,
        prompt: q.prompt,
        inputType: q.input_type,
        options: q.options,
        min: q.min,
        max: q.max,
        unit: q.unit,
        required: !!q.required,
        saveAs: q.save_as,
      })),
    })),
  };
}

export function getSittingModules(sitting: string, script: ConversationScript) {
  return script.modules.filter(m => m.sitting === sitting);
}

export function getSittingQuestions(sitting: string, script: ConversationScript): QuestionDefinition[] {
  return getSittingModules(sitting, script).flatMap(m => m.questions);
}

export function getModuleTitle(moduleId: string, script: ConversationScript): string | undefined {
  return script.modules.find(m => m.id === moduleId)?.title.en;
}

export function getNextQuestionInSitting(
  currentQuestionId: string | null,
  sitting: string,
  script: ConversationScript
): QuestionDefinition | null {
  const questions = getSittingQuestions(sitting, script);
  if (!currentQuestionId) return questions[0] || null;

  const idx = questions.findIndex(q => q.id === currentQuestionId);
  if (idx === -1 || idx + 1 >= questions.length) return null;
  return questions[idx + 1];
}

export function validateAnswer(question: QuestionDefinition, value: any): string | null {
  if (question.required && (value === undefined || value === null || value === '')) {
    return 'This field is required';
  }
  if (typeof value === 'number') {
    if (question.min !== undefined && value < question.min) return `Must be at least ${question.min}`;
    if (question.max !== undefined && value > question.max) return `Must be at most ${question.max}`;
  }
  return null;
}

export function findQuestion(questionId: string, script: ConversationScript): QuestionDefinition | undefined {
  return script.modules.flatMap(m => m.questions).find(q => q.id === questionId);
}
