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

  const response = await fetch(url, { ...options, headers });
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

export interface ComprehensiveMetrics {
  userOverview: {
    totalUsers: number;
    activeToday: number;
    activeThisWeek: number;
    activeThisMonth: number;
    languageDistribution: { language: string; count: number }[];
    avgLoginStreakWeeks: number;
    maxLoginStreakWeeks: number;
    avgAdherenceStreakWeeks: number;
    maxAdherenceStreakWeeks: number;
    perUserLoginStreaks: { displayUserId: string; name: string; streakWeeks: number }[];
    perUserAdherenceStreaks: { displayUserId: string; name: string; streakWeeks: number }[];
  };
  assessments: {
    totalSessions: number;
    completed: number;
    abandoned: number;
    inProgress: number;
    firstAssessmentCompletionRate: number;
    avgCompletionTimeMinutes: number;
    perUserSessions: { userId: string; displayUserId: string; name: string; count: number }[];
    dropOffByQuestion: { questionId: string; moduleId: string; responseCount: number; funnelPercent: number; dropFromFirst: number }[];
  };
  followUps: {
    totalSessions: number;
    due: number;
    completed: number;
    missed: number;
    overdue: number;
    completionRate: number;
    perUserSessions: { displayUserId: string; name: string; total: number; due: number; completed: number }[];
  };
  prescriptions: {
    planDistribution: { planType: string; count: number }[];
    glycemicRisk: { category: string; count: number }[];
    physicalActivityRisk: { category: string; count: number }[];
    sedentaryRisk: { category: string; count: number }[];
    overallRisk: { category: string; count: number }[];
    bmiDistribution: { category: string; count: number }[];
    parQClearanceRequired: number;
    complicationFlags: { totalUsersWithFlags: number; breakdown: Record<string, number> };
  };
  activity: {
    avgMinutesCompleted: number;
    avgDaysCompleted: number;
    strengthAdherence: { totalLogs: number; completedSessions: number; rate: number };
    exerciseAdherenceRate: number;
    avgPrescribedMinutesPerWeek: number;
    avgCompletedVsPrescribed: { prescribedMinutes: number; completedMinutes: number };
  };
  sugarReadings: {
    totalEntries: number;
    fastingCount: number;
    postMealCount: number;
    hba1cCount: number;
    usersWithRecentHba1c: number;
  };
  sugarDistributions: {
    fasting: { below100: number; range100_125: number; above126: number };
    postMeal: { below140: number; range140_199: number; above200: number };
  };
  notifications: {
    reminderOptInRate: number;
    totalUsersWithReminders: number;
    pushSent: number;
    pushDelivered: number;
    pushOpened: number;
    pushActionCompleted: number;
  };
  safety: {
    activitySafetyFlags: number;
    followUpSafetyFlags: number;
    escalationAdviceCount: number;
  };
  weeklyAdherence: {
    weekStart: string;
    userId: string;
    displayUserId: string;
    name: string;
    exerciseAdherent: boolean;
    loginStreakWeeks: number;
    adherenceStreakWeeks: number;
  }[];
}

export interface HealthInfo {
  status: string;
  timestamp: string;
  responseTimeMs: number;
  db: string;
  uptime: number | null;
  cacheEntries: number;
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

  getMetrics: () =>
    adminRequest<{
      totalUsers: number;
      activeUsers: number;
      totalAssessments: number;
      completedAssessments: number;
      completionRate: number;
      averageActivityMinutes: number;
      safetyFlagsTriggered: number;
    }>('/api/admin/metrics/overview'),

  getComprehensiveMetrics: (days: number = 30) =>
    adminRequest<ComprehensiveMetrics>(`/api/admin/metrics/comprehensive?days=${days}`),

  getUsers: (params?: { search?: string; page?: number; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.search) q.set('search', params.search);
    if (params?.page) q.set('page', String(params.page));
    if (params?.limit) q.set('limit', String(params.limit));
    const qs = q.toString();
    return adminRequest<{
      users: Array<{
        id: string;
        displayUserId: string;
        firstName: string;
        lastName: string;
        preferredLanguage: string;
        role: string;
        createdAt: string;
        assessmentsCount: number;
        currentPlan: string;
        followUpsDue: number;
      }>;
      total: number;
      page: number;
      limit: number;
      totalPages: number;
    }>(`/api/admin/users${qs ? '?' + qs : ''}`);
  },

  getUserDetail: (userId: string) =>
    adminRequest<{
      user: any;
      assessments: any[];
      prescriptions: any[];
      sugarReadings: any[];
      activityLogs: any[];
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

  broadcastNotification: (type: 'follow_up' | 'exercise_reminder' | 'sugar_test') =>
    adminRequest<{ type: string; totalUsersWithSubscriptions: number; sent: number; failed: number }>(
      '/api/admin/notifications/broadcast', {
        method: 'POST',
        body: JSON.stringify({ type }),
      }),

  triggerBackup: () =>
    adminRequest<{ message: string }>('/api/admin/backup/trigger', { method: 'POST' }),

  getHealth: () =>
    adminRequest<HealthInfo>('/api/admin/health'),

  cleanupTemporaryAudio: () =>
    adminRequest<{ deleted: number; message: string }>('/api/admin/temporary-audio/cleanup', {
      method: 'POST',
    }),
};
