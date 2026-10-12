import { create } from 'zustand';

// Server-owned Module D lock. Set from any HTTP 423 or from
// /api/safety/user/:id/status -- never persisted locally, never cleared by the
// client on its own: only the server (after clinician acknowledgement) unlocks.
export interface SafetyLock {
  locked: boolean;
  event_code: string | null;
  event_id: string | null;
  open_event_codes: string[];
  language: string;
  emergency_script: string | null;
}

interface SafetyLockState {
  lock: SafetyLock | null;
  setLock: (lock: SafetyLock) => void;
}

export const useSafetyLockStore = create<SafetyLockState>((set) => ({
  lock: null,
  setLock: (lock) => set({ lock: lock.locked ? lock : null }),
}));
