import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { speechProvider } from './SpeechProvider';
import { useVoiceCoachStore } from '../../stores/useVoiceCoachStore';

interface SpeechContextType {
  speak: (text: string, lang?: string, questionId?: string, questionnaireId?: string) => Promise<void>;
  stop: () => void;
  pause: () => void;
  resume: () => void;
  startListening: (lang?: string, inputType?: string) => Promise<void>;
  stopListening: () => void;
  isSpeaking: boolean;
  isPaused: boolean;
  isSupported: boolean;
  isASRSupported: boolean;
}

const SpeechCtx = createContext<SpeechContextType>(null!);

export function SpeechProvider({ children }: { children: ReactNode }) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    speechProvider.onEndCallback = () => {
      if (mountedRef.current) { setIsSpeaking(false); setIsPaused(false); }
    };
    speechProvider.onErrorCallback = () => {
      if (mountedRef.current) { setIsSpeaking(false); setIsPaused(false); }
    };
    speechProvider.onResultCallback = (text, confidence, displayText) => {
      useVoiceCoachStore.getState().setTranscript(text, confidence, displayText);
      useVoiceCoachStore.getState().setFlowState('confirming_transcript');
    };
    return () => { mountedRef.current = false; };
  }, []);

  const ctx: SpeechContextType = {
    speak: async (text, lang, questionId, questionnaireId) => {
      setIsSpeaking(true);
      setIsPaused(false);
      try {
        await speechProvider.speak(text, lang ?? 'en', questionId, questionnaireId);
      } finally {
        if (mountedRef.current) { setIsSpeaking(false); setIsPaused(false); }
      }
    },
    stop: () => { speechProvider.stop(); setIsSpeaking(false); setIsPaused(false); },
    pause: () => { speechProvider.pause(); setIsPaused(true); },
    resume: () => { speechProvider.resume(); setIsPaused(false); },
    startListening: async (lang, inputType) => { await speechProvider.startListening(lang, inputType); },
    stopListening: () => speechProvider.stopListening(),
    isSpeaking,
    isPaused,
    isSupported: speechProvider.isSupported,
    isASRSupported: speechProvider.isASRSupported,
  };

  return <SpeechCtx.Provider value={ctx}>{children}</SpeechCtx.Provider>;
}

export const useSpeech = () => useContext(SpeechCtx);
