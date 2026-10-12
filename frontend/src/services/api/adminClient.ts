const API_BASE = import.meta.env.VITE_API_URL || "";
const ADMIN_TOKEN_KEY = 'df_admin_token';

function getToken(): string | null {
  return localStorage.getItem(ADMIN_TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(ADMIN_TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(ADMIN_TOKEN_KEY);
}

export function isAdminLoggedIn(): boolean {
  return !!getToken();
}

async function adminRequest<T>(url: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${url}`, { ...options, headers });
  if (response.status === 401) {
    clearToken();
    throw new Error('Unauthorized');
  }
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }
  return response.json();
}

export interface OverviewMetrics {
  totalUsers: number;
  activeToday: number;
  activeThisWeek: number;
  baselineCompleted: number;
  conversationSessionsCompleted: number;
  conversationSessionsInProgress: number;
  riskTierDistribution: { tier: string; count: number }[];
  checkinsCompleted: number;
  checkinsMissed: number;
  checkinsEscalated: number;
  openSafetyEvents: number;
  reassessmentsTriggered: number;
}

export interface SafetyEventRow {
  id: string;
  userId: string;
  displayUserId?: string;
  firstName?: string;
  lastName?: string;
  triggerCode: string;
  sourceModule: string;
  status: 'open' | 'acknowledged';
  resolved: boolean;
  triggeredAt: string;
  acknowledgedAt: string | null;
  acknowledgedBy: string | null;
  acknowledgementNote: string | null;
}

export interface HealthInfo {
  status: string;
  timestamp: string;
  responseTimeMs: number;
  db: string;
  cacheEntries: number;
}

export interface ExportResponseRow {
  displayUserId: string;
  firstName: string;
  lastName: string;
  sitting: string;
  moduleId: string;
  questionId: string;
  questionTextEn: string | null;
  answerValue: string;
  language: string;
  inputModality: string;
  answeredAt: string | null;
}

export interface ExportCheckinRow {
  displayUserId: string;
  firstName: string;
  lastName: string;
  programWeek: number;
  dueDate: string | null;
  status: string;
  activityDays: number | null;
  foodGoalDays: number | null;
  medicationDays: number | null;
  footCareDays: number | null;
  newFootProblem: boolean | null;
  stress0to10: number | null;
  sleep0to10: number | null;
  sugarReading: number | null;
  hypoEpisode: boolean | null;
  safetyFlag: boolean;
  completedAt: string | null;
}

export interface AdminUserRow {
  id: string;
  displayUserId: string;
  firstName: string;
  lastName: string;
  preferredLanguage: string;
  role: string;
  createdAt: string;
  riskTier: string;
  checkinsDue: number;
}

export function exportToCsv(data: Record<string, any>[], filename: string) {
  if (!data.length) return;
  const headers = Object.keys(data[0]);
  const csvRows = [headers.join(',')];
  for (const row of data) {
    csvRows.push(headers.map(h => {
      const val = row[h];
      const s = val == null ? '' : String(val);
      return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s;
    }).join(','));
  }
  const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const adminApi = {
  login: (username: string, password: string) =>
    adminRequest<{ token: string; adminId: string; displayName: string; role: string }>('/api/admin/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  getOverviewMetrics: (forceRefresh = false) =>
    adminRequest<OverviewMetrics>(`/api/admin/metrics/overview${forceRefresh ? '?force_refresh=true' : ''}`),

  getUsers: (params?: { search?: string; page?: number; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.search) q.set('search', params.search);
    if (params?.page) q.set('page', String(params.page));
    if (params?.limit) q.set('limit', String(params.limit));
    const qs = q.toString();
    return adminRequest<{
      users: AdminUserRow[];
      total: number;
      page: number;
      limit: number;
      totalPages: number;
    }>(`/api/admin/users${qs ? '?' + qs : ''}`);
  },

  getUserDetail: (userId: string) =>
    adminRequest<{
      user: any;
      baselineProfile: any;
      carePlans: any[];
      checkinSessions: any[];
      safetyEvents: any[];
    }>(`/api/admin/users/${userId}/detail`),

  getMissingAudio: () =>
    adminRequest<{ missing: Array<{ questionnaireId: string; questionnaireVersion: string; questionId: string; language: string }>; total: number }>(
      '/api/admin/audio-assets/missing'
    ),

  generateAudio: (body?: { questionnaire_id?: string; language?: string; force_regen?: boolean }) =>
    adminRequest<{ generated: number; skipped: number; failed: number; errors: string[] }>('/api/admin/audio-assets/generate', {
      method: 'POST',
      body: JSON.stringify(body || {}),
    }),

  broadcastNotification: (type: 'checkin' | 'medication_reminder' | 'sugar_test') =>
    adminRequest<{ type: string; totalUsersWithSubscriptions: number; sent: number; failed: number }>(
      '/api/admin/notifications/broadcast', {
        method: 'POST',
        body: JSON.stringify({ type }),
      }),

  triggerBackup: () =>
    adminRequest<{ message: string }>('/api/admin/backup/trigger', { method: 'POST' }),

  getHealth: () =>
    adminRequest<HealthInfo>('/api/admin/health'),

  exportResponses: () =>
    adminRequest<ExportResponseRow[]>('/api/admin/export/responses'),

  exportCheckins: () =>
    adminRequest<ExportCheckinRow[]>('/api/admin/export/checkins'),

  cleanupTemporaryAudio: () =>
    adminRequest<{ deleted: number; message: string }>('/api/admin/temporary-audio/cleanup', {
      method: 'POST',
    }),

  getSafetyEvents: (status: 'open' | 'acknowledged' | 'all' = 'open') =>
    adminRequest<SafetyEventRow[]>(`/api/admin/safety-events?status=${status}`),

  // The only way a patient's coaching lock is lifted.
  acknowledgeSafetyEvent: (eventId: string, note: string) =>
    adminRequest<SafetyEventRow & { patientStillLocked: boolean }>(`/api/admin/safety-events/${eventId}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),

  changePassword: (currentPassword: string, newPassword: string) =>
    adminRequest<{ message: string }>('/api/admin/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),
};
