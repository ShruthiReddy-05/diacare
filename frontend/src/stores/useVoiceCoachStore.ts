import { create } from 'zustand';

export type VoiceFlowState =
  | 'idle'
  | 'loading_audio'
  | 'speaking_question'
  | 'paused'
  | 'listening'
  | 'confirming_transcript'
  | 'validating_answer'
  | 'advancing'
  | 'error'
  | 'stopped';

interface VoiceCoachStore {
  flowState: VoiceFlowState;
  transcript: string;
  displayText: string;
  confidence: number;
  isEnabled: boolean;

  setFlowState: (state: VoiceFlowState) => void;
  setTranscript: (text: string, confidence?: number, displayText?: string) => void;
  toggleEnabled: () => void;
  enable: () => void;
  disable: () => void;
  reset: () => void;
}

export const useVoiceCoachStore = create<VoiceCoachStore>((set) => ({
  flowState: 'idle',
  transcript: '',
  displayText: '',
  confidence: 0,
  isEnabled: false,

  setFlowState: (flowState) => set({ flowState }),
  setTranscript: (transcript, confidence = 1, displayText) => set({ transcript, confidence, displayText: displayText ?? transcript }),
  toggleEnabled: () => set((s) => ({ isEnabled: !s.isEnabled, flowState: s.isEnabled ? 'stopped' : 'idle' })),
  enable: () => set({ isEnabled: true, flowState: 'idle' }),
  disable: () => set({ isEnabled: false, flowState: 'stopped' }),
  reset: () => set({ flowState: 'idle', transcript: '', displayText: '', confidence: 0 }),
}));
