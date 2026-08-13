import { create } from 'zustand';
import type { UserProfile, LanguageCode } from '../domain/types';
import { db } from '../services/storage/localDb';
import { api } from '../services/api/client';

interface UserState {
  user: UserProfile | null;
  language: LanguageCode;
  theme: 'dark' | 'light';
  isRegistered: boolean;
  isLoading: boolean;
  voiceConsentGiven: boolean;
  loadFromLocal: () => Promise<void>;
  register: (firstName: string, lastName: string, language: LanguageCode) => Promise<UserProfile>;
  recover: (displayUserId: string, firstName: string, lastName: string) => Promise<UserProfile>;
  setLanguage: (lang: LanguageCode) => Promise<void>;
  setTheme: (theme: 'dark' | 'light') => Promise<void>;
  setVoiceConsent: (given: boolean) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: UserProfile) => void;
}

export const useUserStore = create<UserState>((set, get) => ({
  user: null,
  language: 'en',
  theme: 'dark',
  isRegistered: false,
  isLoading: true,
  voiceConsentGiven: false,

  loadFromLocal: async () => {
    try {
      const stored = await db.settings.get('userProfile');
      const lang = (await db.settings.get('language'))?.value || 'en';
      const theme = (await db.settings.get('theme'))?.value || 'dark';
      const voiceConsent = (await db.settings.get('voiceConsent'))?.value === '1';
      document.documentElement.setAttribute('data-theme', theme);
      if (stored?.value) {
        set({ user: stored.value as UserProfile, language: lang as LanguageCode, theme: theme as 'dark' | 'light', isRegistered: true, isLoading: false, voiceConsentGiven: voiceConsent });
        api.createAppSession(stored.value.id, { entry_source: 'direct', language: lang }).catch((e) => console.warn('createAppSession (loadFromLocal) failed:', e));
      } else {
        set({ language: lang as LanguageCode, theme: theme as 'dark' | 'light', isLoading: false, voiceConsentGiven: voiceConsent });
      }
    } catch {
      set({ isLoading: false });
    }
  },

  setVoiceConsent: async (given) => {
    await db.settings.put({ key: 'voiceConsent', value: given ? '1' : '0' });
    set({ voiceConsentGiven: given });
  },

  setTheme: async (theme) => {
    await db.settings.put({ key: 'theme', value: theme });
    document.documentElement.setAttribute('data-theme', theme);
    set({ theme });
  },

  register: async (firstName, lastName, language) => {
    const res = await api.registerUser({ first_name: firstName, last_name: lastName, preferred_language: language });
    const profile: UserProfile = {
      id: res.id,
      display_user_id: res.display_user_id,
      first_name: res.first_name,
      last_name: res.last_name,
      preferred_language: res.preferred_language,
      role: res.role || 'participant',
    };
    await db.settings.put({ key: 'userProfile', value: profile });
    await db.settings.put({ key: 'language', value: language });
    api.createAppSession(res.id, { entry_source: 'direct', language }).catch((e) => console.warn('createAppSession (register) failed:', e));
    set({ user: profile, language, isRegistered: true });
    return profile;
  },

  recover: async (displayUserId, firstName, lastName) => {
    const res = await api.recoverUser({ display_user_id: displayUserId, first_name: firstName, last_name: lastName });
    const profile: UserProfile = {
      id: res.id,
      display_user_id: res.display_user_id,
      first_name: res.first_name,
      last_name: res.last_name,
      preferred_language: res.preferred_language,
      role: res.role || 'participant',
    };
    await db.settings.put({ key: 'userProfile', value: profile });
    await db.settings.put({ key: 'language', value: res.preferred_language });
    api.createAppSession(res.id, { entry_source: 'direct', language: res.preferred_language }).catch((e) => console.warn('createAppSession (recover) failed:', e));
    set({ user: profile, language: res.preferred_language, isRegistered: true });
    return profile;
  },

  setLanguage: async (lang) => {
    await db.settings.put({ key: 'language', value: lang });
    set({ language: lang });
    const user = get().user;
    if (user) {
      api.updateLanguage(user.id, lang).catch(() => { });
    }
  },

  logout: async () => {
    await db.settings.delete('userProfile');
    set({ user: null, isRegistered: false });
  },

  setUser: (user) => set({ user, isRegistered: true }),
}));
