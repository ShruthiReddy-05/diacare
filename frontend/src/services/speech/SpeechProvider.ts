export class SpeechProvider {
  private synth: SpeechSynthesis | null = null;
  private recognition: any = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private utterance: SpeechSynthesisUtterance | null = null;
  private currentAudio: HTMLAudioElement | null = null;
  private onEnd: (() => void) | null = null;
  private onResult: ((text: string, confidence: number, displayText?: string) => void) | null = null;
  private onError: ((error: string) => void) | null = null;
  private currentLang: string = 'en';
  private isSarvamListening: boolean = false;
  private ttsFailed: boolean = false;

  constructor() {
    if ('speechSynthesis' in window) {
      this.synth = window.speechSynthesis;
    }
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.lang = 'en-IN';
    }
  }

  get isSupported(): boolean {
    return !!this.synth;
  }

  get isASRSupported(): boolean {
    return !!(this.recognition || typeof MediaRecorder !== 'undefined');
  }

  speak(text: string, lang: string = 'en', questionId?: string, questionnaireId?: string): Promise<void> {
    if (questionId && questionnaireId) {
      return this.speakWithAsset(text, lang, questionId, questionnaireId);
    }
    return this.speakWithFallback(text, lang);
  }

  private async speakWithAsset(text: string, lang: string, questionId: string, questionnaireId: string): Promise<void> {
    try {
      const resp = await fetch(`/api/audio-assets/lookup?questionnaire_id=${encodeURIComponent(questionnaireId)}&question_id=${encodeURIComponent(questionId)}&language=${encodeURIComponent(lang)}`);
      if (resp.ok) {
        const data = await resp.json();
        const audioResp = await fetch(data.fileUrl);
        if (audioResp.ok) {
          const blob = await audioResp.blob();
          const url = URL.createObjectURL(blob);
          return this.playAudioUrl(url);
        }
      }
    } catch {
      // fall through
    }
    return this.speakWithFallback(text, lang);
  }

  private playAudioUrl(url: string): Promise<void> {
    this.currentAudio?.pause();
    const audio = new Audio(url);
    this.currentAudio = audio;
    return new Promise((resolve, reject) => {
      audio.onended = () => {
        if (this.currentAudio === audio) this.currentAudio = null;
        URL.revokeObjectURL(url);
        this.onEnd?.();
        resolve();
      };
      audio.onerror = () => {
        if (this.currentAudio === audio) this.currentAudio = null;
        URL.revokeObjectURL(url);
        this.onError?.('Audio playback error');
        reject(new Error('Audio playback error'));
      };
      audio.play().catch((e) => {
        if (this.currentAudio === audio) this.currentAudio = null;
        URL.revokeObjectURL(url);
        this.onError?.(e.message);
        reject(e);
      });
    });
  }

  private speakWithFallback(text: string, lang: string): Promise<void> {
    if (lang === 'ta' || this.ttsFailed) {
      return this.speakWithSarvam(text, lang);
    }
    return this.speakWithWebSpeech(text, lang);
  }

  private speakWithWebSpeech(text: string, lang: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.synth) {
        reject(new Error('Speech synthesis not supported'));
        return;
      }
      this.synth.cancel();
      this.utterance = new SpeechSynthesisUtterance(text);
      this.utterance.lang = lang === 'ta' ? 'ta-IN' : 'en-IN';
      this.utterance.rate = 0.9;
      this.utterance.pitch = 1;
      this.utterance.onend = () => {
        this.onEnd?.();
        resolve();
      };
      this.utterance.onerror = (e) => {
        this.onError?.(e.error);
        reject(new Error(e.error));
      };
      this.synth.speak(this.utterance);
    });
  }

  private async speakWithSarvam(text: string, lang: string = 'ta'): Promise<void> {
    const languageCode = lang === 'en' ? 'en-IN' : 'ta-IN';
    const response = await fetch('/api/speech/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, target_language_code: languageCode, speaker: 'shubh', model: 'bulbul:v3', pace: 1.0 }),
    });
    if (!response.ok) {
      const errText = await response.text().catch(() => 'TTS failed');
      this.onError?.(errText);
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    return this.playAudioUrl(url);
  }

  stop(): void {
    this.synth?.cancel();
    this.stopListening();
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }
  }

  pause(): void {
    this.synth?.pause();
    if (this.currentAudio && !this.currentAudio.paused) {
      this.currentAudio.pause();
    }
  }

  resume(): void {
    this.synth?.resume();
    if (this.currentAudio && this.currentAudio.paused) {
      this.currentAudio.play().catch(() => {});
    }
  }

  get isSpeaking(): boolean {
    return this.synth?.speaking ?? false;
  }

  get isPaused(): boolean {
    return this.synth?.paused ?? false;
  }

  private readonly GRAMMARS: Record<string, string> = {
    confirmation: `#JSGF V1.0; grammar yesno; public <answer> = yes | no | yeah | yep | nah | nope;`,
    single_choice: `#JSGF V1.0; grammar choice; public <answer> = low | high | moderate | male | female | walking | cycling | yoga | swimming | running | yes | no;`,
    multi_choice: `#JSGF V1.0; grammar choice; public <answer> = low | high | moderate | male | female | walking | cycling | yoga | swimming | running | yes | no;`,
    number: `#JSGF V1.0; grammar number; public <answer> = zero | one | two | three | four | five | six | seven | eight | nine | ten | twelve | fifteen | twenty | thirty | forty | fifty | sixty | seventy | eighty | ninety | hundred;`,
    height: `#JSGF V1.0; grammar height; public <answer> = one | two | three | four | five | six | hundred | fifty | sixty | seventy | eighty | point;`,
    weight: `#JSGF V1.0; grammar weight; public <answer> = zero | one | two | three | four | five | six | seven | eight | nine | ten | twenty | thirty | forty | fifty | sixty | seventy | eighty | ninety | hundred | point;`,
  };

  private setGrammar(inputType?: string): void {
    if (!this.recognition || !(window as any).SpeechGrammarList) return;
    const jsgf = this.GRAMMARS[inputType || ''] || this.GRAMMARS.confirmation;
    const grammarList = new (window as any).SpeechGrammarList();
    grammarList.addFromString(jsgf, 1);
    this.recognition.grammars = grammarList;
  }

  async startListening(lang: string = 'en', inputType?: string): Promise<void> {
    this.currentLang = lang;
    this.setGrammar(inputType);
    if (lang === 'ta') {
      await this.startSarvamListening();
    } else {
      this.startWebSpeechListening(lang);
    }
  }

  private startWebSpeechListening(lang: string = 'en'): void {
    if (!this.recognition) return;
    this.recognition.lang = lang === 'ta' ? 'ta-IN' : 'en-IN';

    this.recognition.onresult = (event: any) => {
      const last = event.results.length - 1;
      const result = event.results[last];
      let text = '';
      let confidence = 0;
      for (let i = 0; i < result.length; i++) {
        const alt = result[i].transcript.trim().toLowerCase();
        if (alt === 'yes' || alt === 'no' || alt === 'yeah' || alt === 'yep' || alt === 'nah' || alt === 'nope') {
          text = alt;
          confidence = 1;
          break;
        }
        if (!text) {
          text = result[i].transcript;
          confidence = result[i].confidence;
        }
      }
      this.onResult?.(text, confidence);
    };
    this.recognition.onerror = (event: any) => {
      this.onError?.(event.error);
    };
    try {
      this.recognition.start();
    } catch {
      // already started
    }
  }

  private async startSarvamListening(): Promise<void> {
    if (!navigator.mediaDevices?.getUserMedia) {
      this.onError?.('Microphone not available');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.audioChunks = [];
      this.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) this.audioChunks.push(e.data);
      };
      this.mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        if (this.audioChunks.length === 0) return;
        const blob = new Blob(this.audioChunks, { type: 'audio/webm;codecs=opus' });
        this.audioChunks = [];
        await this.sendToSarvamAsr(blob);
      };
      this.mediaRecorder.start();
      this.isSarvamListening = true;
      setTimeout(() => {
        if (this.isSarvamListening && this.mediaRecorder?.state === 'recording') {
          this.mediaRecorder.stop();
          this.isSarvamListening = false;
        }
      }, 5000);
    } catch {
      this.onError?.('Microphone access denied');
    }
  }

  private async sendToSarvamAsr(blob: Blob): Promise<void> {
    try {
      const buffer = await blob.arrayBuffer();
      const bytes = new Uint8Array(buffer);
      let binary = '';
      for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
      const audioBase64 = btoa(binary);
      const response = await fetch('/api/speech/asr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audio_base64: audioBase64, language: 'ta-IN' }),
      });
      if (!response.ok) {
        this.onError?.('Sarvam ASR failed');
        return;
      }
      const data = await response.json();
      const transcript = data?.transcript || data?.text || '';
      const displayText = data?.display_text || transcript;
      const confidence = data?.confidence ?? 1;
      this.onResult?.(transcript, confidence, displayText);
    } catch {
      this.onError?.('Sarvam ASR network error');
    }
  }

  stopListening(): void {
    if (this.currentLang === 'ta') {
      this.isSarvamListening = false;
      if (this.mediaRecorder?.state === 'recording') {
        this.mediaRecorder.stop();
      }
    } else {
      try {
        this.recognition?.stop();
      } catch {
        // ignore
      }
    }
  }

  set onEndCallback(cb: () => void) { this.onEnd = cb; }
  set onResultCallback(cb: (text: string, confidence: number, displayText?: string) => void) { this.onResult = cb; }
  set onErrorCallback(cb: (error: string) => void) { this.onError = cb; }
}

export const speechProvider = new SpeechProvider();
