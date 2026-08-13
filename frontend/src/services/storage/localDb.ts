import Dexie, { type Table } from 'dexie';

export interface LocalSetting {
  key: string;
  value: any;
}

export interface LocalAssessmentSession {
  id: string;
  user_id: string;
  questionnaire_id: string;
  questionnaire_version: string;
  status: string;
  started_at: string;
  completed_at?: string;
  responses: any[];
}

export interface LocalSugarReading {
  id?: number;
  user_id: string;
  reading_type: string;
  value: number;
  recorded_at: string;
  notes?: string;
  synced: number; // 0 = unsynced, 1 = synced
}

export interface LocalActivityLog {
  id?: number;
  user_id: string;
  activity_date: string;
  completed_minutes: number;
  completed_days: number;
  strength_completed: boolean;
  fatigue_rating?: number;
  difficulty_rating?: number;
  safety_flag: boolean;
  notes?: string;
  synced: number; // 0 = unsynced, 1 = synced
}

export class DiaFitDatabase extends Dexie {
  settings!: Table<LocalSetting>;
  assessmentSessions!: Table<LocalAssessmentSession>;
  sugarReadings!: Table<LocalSugarReading>;
  activityLogs!: Table<LocalActivityLog>;

  constructor() {
    super('DiaFitDatabase');
    this.version(1).stores({
      settings: 'key',
      assessmentSessions: 'id, user_id, status',
      sugarReadings: '++id, user_id, reading_type, synced',
      activityLogs: '++id, user_id, activity_date, synced'
    });
  }
}

export const db = new DiaFitDatabase();
