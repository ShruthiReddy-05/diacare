// In local dev this stays "" and vite.config.ts's proxy forwards /api to localhost:8000.
// In production, set VITE_API_URL to the deployed backend's origin (e.g. https://diafit-api.onrender.com).
const API_BASE = import.meta.env.VITE_API_URL || "";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers = {
    "Content-Type": "application/json",
    ...(options?.headers || {})
  };

  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    let errorDetail = "API Request failed";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // Users
  registerUser: (data: { first_name: string; last_name: string; preferred_language: string }) =>
    request<any>("/api/users/register", {
      method: "POST",
      body: JSON.stringify(data)
    }),

  recoverUser: (data: { display_user_id: string; first_name: string; last_name: string }) =>
    request<any>("/api/users/recover", {
      method: "POST",
      body: JSON.stringify(data)
    }),

  getUser: (userId: string) => request<any>(`/api/users/${userId}`),

  createAppSession: (userId: string, data: { entry_source?: string; language?: string }) =>
    request<any>(`/api/users/${userId}/sessions`, {
      method: "POST",
      body: JSON.stringify(data)
    }),

  updateLanguage: (userId: string, preferred_language: string) =>
    request<any>(`/api/users/${userId}/language`, {
      method: "PATCH",
      body: JSON.stringify({ preferred_language })
    }),

  // Conversation (onboarding + baseline B1-B3 + M1-M4, across 3 sittings)
  getScript: () => request<any>("/api/conversation/script"),

  createConversationSession: (userId: string, data: { script_id: string; script_version: string; sitting: string; preferred_checkin_time?: string }) =>
    request<any>(`/api/conversation/sessions?user_id=${userId}`, {
      method: "POST",
      body: JSON.stringify(data)
    }),

  submitConversationResponse: (sessionId: string, data: {
    module_id: string;
    question_id: string;
    question_text_en?: string;
    question_text_ta?: string;
    answer_value: string;
    answer_display_label?: { en: string; ta: string } | null;
    language: string;
    input_modality?: string;
  }) =>
    request<any>(`/api/conversation/sessions/${sessionId}/responses`, {
      method: "POST",
      body: JSON.stringify(data)
    }),

  completeSitting: (sessionId: string, sitting: string) =>
    request<any>(`/api/conversation/sessions/${sessionId}/complete-sitting`, {
      method: "POST",
      body: JSON.stringify({ sitting })
    }),

  getConversationSession: (sessionId: string) =>
    request<any>(`/api/conversation/sessions/${sessionId}`),

  getUserConversationSessions: (userId: string) =>
    request<any[]>(`/api/conversation/user/${userId}`),

  // Care Plan
  generateCarePlan: (userId: string) =>
    request<any>(`/api/care-plan/generate?user_id=${userId}`, {
      method: "POST"
    }),

  getCarePlan: (carePlanId: string) =>
    request<any>(`/api/care-plan/${carePlanId}`),

  getLatestCarePlan: (userId: string) =>
    request<any>(`/api/care-plan/user/${userId}/latest`),

  getCarePlanTts: (carePlanId: string, language?: string) =>
    request<{ asset_id: string }>(`/api/care-plan/${carePlanId}/tts`, {
      method: "POST",
      body: JSON.stringify({ language: language || "en-IN" }),
    }),

  getTemporaryAudioUrl: (assetId: string) =>
    `/api/temporary-audio/${assetId}`,

  // Weekly Check-In
  getNextCheckIn: (userId: string) =>
    request<any>(`/api/checkin/user/${userId}/next`),

  completeCheckIn: (sessionId: string, data: {
    q1_activity_days: number;
    q2_food_goal_days: number;
    q3_medication_days: number;
    q4_foot_care_days: number;
    q5_new_foot_problem: boolean;
    q6_stress_0_10: number;
    q7_sleep_0_10: number;
    q8_sugar_reading?: number | null;
    q8b_hypo_episode?: boolean;
    fever_or_vomiting_reported?: boolean;
    upcoming_function_or_fasting?: boolean;
  }) =>
    request<any>(`/api/checkin/sessions/${sessionId}/complete`, {
      method: "POST",
      body: JSON.stringify(data)
    }),

  getCheckInSessions: (userId: string) =>
    request<any[]>(`/api/checkin/user/${userId}/sessions`),

  getCheckInSchedule: (userId: string) =>
    request<any>(`/api/checkin/user/${userId}/schedule`),

  createCheckInSchedule: (userId: string, preferredTime: string = "evening") =>
    request<any>(`/api/checkin/user/${userId}/schedule?preferred_time=${encodeURIComponent(preferredTime)}`, {
      method: "POST"
    }),

  // Tracking
  addSugarReading: (userId: string, data: { reading_type: string; value: number; notes?: string }) =>
    request<any>(`/api/tracking/sugar?user_id=${userId}`, {
      method: "POST",
      body: JSON.stringify(data)
    }),

  getUserSugarReadings: (userId: string) =>
    request<any[]>(`/api/tracking/sugar/user/${userId}`),

  logActivity: (userId: string, data: {
    activity_date: string;
    completed_minutes: number;
    completed_days: number;
    strength_completed: boolean;
    fatigue_rating?: number;
    difficulty_rating?: number;
    safety_flag: boolean;
    notes?: string;
  }) =>
    request<any>(`/api/tracking/activity?user_id=${userId}`, {
      method: "POST",
      body: JSON.stringify(data)
    }),

  getUserActivityLogs: (userId: string) =>
    request<any[]>(`/api/tracking/activity/user/${userId}`),

  // Admin
  getAdminMetrics: () => request<any>("/api/admin/metrics/overview"),
  getAdminUsers: () => request<any[]>("/api/admin/users"),
  getAdminUserDetail: (userId: string) => request<any>(`/api/admin/users/${userId}/detail`),

  // Notifications
  getVapidPublicKey: () =>
    request<{ publicKey: string }>("/api/notifications/vapid-public-key"),

  subscribePush: (userId: string, data: {
    endpoint: string;
    p256dh_key: string;
    auth_key: string;
    device_type?: string;
  }) =>
    request<any>(`/api/notifications/subscribe?user_id=${userId}`, {
      method: "POST",
      body: JSON.stringify(data)
    }),

  unsubscribePush: (userId: string, endpoint: string) =>
    request<any>(`/api/notifications/subscribe?user_id=${userId}&endpoint=${encodeURIComponent(endpoint)}`, {
      method: "DELETE"
    }),

  // Reminders
  getReminders: (userId: string) =>
    request<any[]>(`/api/reminders/user/${userId}`),

  createReminder: (userId: string, data: {
    type: string;
    label?: string;
    time_of_day?: string;
    days_of_week?: number[];
    interval_days?: number;
    is_enabled: boolean;
  }) =>
    request<any>(`/api/reminders/user/${userId}`, {
      method: "POST",
      body: JSON.stringify(data)
    }),

  updateReminder: (userId: string, reminderId: string, data: {
    type: string;
    label?: string;
    time_of_day?: string;
    days_of_week?: number[];
    interval_days?: number;
    is_enabled: boolean;
  }) =>
    request<any>(`/api/reminders/user/${userId}/${reminderId}`, {
      method: "PUT",
      body: JSON.stringify(data)
    }),

  // Adherence (per-domain streaks, keyed to program_week)
  getCurrentAdherence: (userId: string) =>
    request<any>(`/api/adherence/user/${userId}/current`),

  getAdherenceHistory: (userId: string) =>
    request<any[]>(`/api/adherence/user/${userId}/history`),
};
export default api;
