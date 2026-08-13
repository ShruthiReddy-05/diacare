import type { QuestionDefinition, QuestionnaireDefinition, ValidationRule } from './types';

export function getModuleProgress(moduleId: string, answers: Record<string, any>, questionnaire: QuestionnaireDefinition): number {
  const mod = questionnaire.modules.find(m => m.id === moduleId);
  if (!mod) return 0;
  const total = mod.questions.filter(q => q.required).length;
  if (total === 0) return 100;
  const done = mod.questions.filter(q => q.required && answers[q.saveAs] !== undefined && answers[q.saveAs] !== null && answers[q.saveAs] !== '').length;
  return Math.round((done / total) * 100);
}

export function isModuleComplete(moduleId: string, answers: Record<string, any>, questionnaire: QuestionnaireDefinition): boolean {
  return getModuleProgress(moduleId, answers, questionnaire) === 100;
}

export function getCurrentModuleId(currentQuestionId: string, questionnaire: QuestionnaireDefinition): string | null {
  for (const mod of questionnaire.modules) {
    if (mod.questions.some(q => q.id === currentQuestionId)) return mod.id;
  }
  return null;
}

function followsBranching(question: QuestionDefinition, answers: Record<string, any>, allQuestions: QuestionDefinition[]): boolean {
  if (!question.branching) return true;
  for (const rule of question.branching) {
    // Resolve dependsOn (question_id) to the actual saveAs key used in the answers dict
    const dependsQ = allQuestions.find(q => q.id === rule.dependsOn);
    const key = dependsQ?.saveAs || rule.dependsOn;
    const val = answers[key];
    if (rule.equals !== undefined && val === rule.equals) return false;
    if (rule.notEquals !== undefined && val !== rule.notEquals) return false;
  }
  return true;
}

export function getNextQuestion(currentQuestionId: string | null, answers: Record<string, any>, questionnaire: QuestionnaireDefinition): QuestionDefinition | null {
  const allQuestions = questionnaire.modules.flatMap(m => m.questions);
  if (!currentQuestionId) return allQuestions.find(q => followsBranching(q, answers, allQuestions)) || null;

  const currentIdx = allQuestions.findIndex(q => q.id === currentQuestionId);
  if (currentIdx === -1) return null;

  for (let i = currentIdx + 1; i < allQuestions.length; i++) {
    if (followsBranching(allQuestions[i], answers, allQuestions)) return allQuestions[i];
  }
  return null;
}

export function getModuleQuestions(moduleId: string, questionnaire: QuestionnaireDefinition): QuestionDefinition[] {
  const mod = questionnaire.modules.find(m => m.id === moduleId);
  return mod?.questions || [];
}

function applyValidation(rule: ValidationRule, value: any): string | null {
  const msg = rule.message.en;
  if (typeof value === 'string') value = value.trim();

  switch (rule.type) {
    case 'required':
      return (value === undefined || value === null || value === '') ? msg : null;
    case 'min':
      return (typeof value === 'number' && value < rule.value) ? msg : null;
    case 'max':
      return (typeof value === 'number' && value > rule.value) ? msg : null;
    case 'regex':
      return (typeof value === 'string' && rule.value && !new RegExp(rule.value).test(value)) ? msg : null;
    default:
      return null;
  }
}

export function validateAnswer(question: QuestionDefinition, value: any): string | null {
  if (!value && value !== 0 && question.required) {
    return question.validation?.find(v => v.type === 'required')?.message.en || 'This field is required';
  }
  if (question.validation) {
    for (const rule of question.validation) {
      const err = applyValidation(rule, value);
      if (err) return err;
    }
  }
  return null;
}

export function getAllQuestionIds(questionnaire: QuestionnaireDefinition): string[] {
  return questionnaire.modules.flatMap(m => m.questions.map(q => q.id));
}
