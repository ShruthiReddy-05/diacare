import type { VoiceFlowState } from '../../stores/useVoiceCoachStore';

export function canTransition(from: VoiceFlowState, to: VoiceFlowState): boolean {
  const transitions: Record<VoiceFlowState, VoiceFlowState[]> = {
    idle: ['loading_audio', 'stopped'],
    loading_audio: ['speaking_question', 'error', 'stopped'],
    speaking_question: ['listening', 'paused', 'stopped'],
    paused: ['speaking_question', 'stopped'],
    listening: ['confirming_transcript', 'validating_answer', 'error', 'stopped'],
    confirming_transcript: ['validating_answer', 'listening', 'stopped'],
    validating_answer: ['advancing', 'speaking_question', 'stopped'],
    advancing: ['loading_audio', 'idle', 'stopped'],
    error: ['idle', 'stopped'],
    stopped: ['idle'],
  };
  return transitions[from]?.includes(to) ?? false;
}

export function getNextStateOnAnswer(current: VoiceFlowState, isValid: boolean): VoiceFlowState {
  if (current === 'listening' || current === 'confirming_transcript') {
    return isValid ? 'validating_answer' : 'speaking_question';
  }
  return current;
}

export function getNextStateOnAdvance(current: VoiceFlowState, hasNext: boolean): VoiceFlowState {
  if (current === 'advancing') {
    return hasNext ? 'loading_audio' : 'idle';
  }
  return current;
}
