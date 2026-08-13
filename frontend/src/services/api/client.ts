const API_BASE = ""; // Since we configure proxy in vite.config.ts, routes like /api/users/... will automatically route to localhost:8000

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

  // Assessments
  createAssessmentSession: (userId: string, data: { questionnaire_id: string; questionnaire_version: string }) =>
    request<any>(`/api/assessments/sessions?user_id=${userId}`, {
      method: "POST",
      body: JSON.stringify(data)
    }),
    
  submitResponse: (sessionId: string, data: {
    question_id: string;
    module_id: string;
    question_text_en?: string;
    question_text_ta?: string;
    answer_value: string;
    answer_display_label?: { en: string; ta: string } | null;
    language: string;
  }) =>
    request<any>(`/api/assessments/sessions/${sessionId}/responses`, {
      method: "POST",
      body: JSON.stringify(data)
    }),
    
  completeAssessment: (sessionId: string) =>
    request<any>(`/api/assessments/sessions/${sessionId}/complete`, {
      method: "POST"
    }),
    
  getAssessmentSession: (sessionId: string) =>
    request<any>(`/api/assessments/sessions/${sessionId}`),
    
  getUserAssessments: (userId: string) =>
    request<any[]>(`/api/assessments/user/${userId}`),

  // Prescriptions
  generatePrescription: (sessionId: string, language?: string) =>
    request<any>(`/api/prescriptions/generate?session_id=${sessionId}&language=${language || 'en'}`, {
      method: "POST"
    }),
    
  getPrescription: (prescriptionId: string) =>
    request<any>(`/api/prescriptions/${prescriptionId}`),
    
  getLatestPrescription: (userId: string) =>
    request<any>(`/api/prescriptions/user/${userId}/latest`),

  getPrescriptionTts: (prescriptionId: string, language?: string) =>
    request<{ asset_id: string }>(`/api/prescriptions/${prescriptionId}/tts`, {
      method: "POST",
      body: JSON.stringify({ language: language || "en-IN" }),
    }),

  getTemporaryAudioUrl: (assetId: string) =>
    `/api/temporary-audio/${assetId}`,

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

  // Language
  updateLanguage: (userId: string, preferred_language: string) =>
    request<any>(`/api/users/${userId}/language`, {
      method: "PATCH",
      body: JSON.stringify({ preferred_language })
    }),

  // Follow-Ups
  getNextFollowUp: (userId: string) =>
    request<any>(`/api/follow-ups/user/${userId}/next`),

  completeFollowUp: (sessionId: string, data: {
    q1_walked?: boolean | null;
    q2_difficulty?: number | null;
    q3_chest_pain_dizziness?: boolean | null;
    q4_foot_wounds?: boolean | null;
  }) =>
    request<any>(`/api/follow-ups/sessions/${sessionId}/complete`, {
      method: "POST",
      body: JSON.stringify(data)
    }),

  getFollowUpSessions: (userId: string) =>
    request<any[]>(`/api/follow-ups/user/${userId}/sessions`),

  createFollowUpSchedule: (userId: string) =>
    request<any>(`/api/follow-ups/user/${userId}/schedule`, {
      method: "POST"
    }),

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
    days_of_week?: number[];
    interval_days?: number;
    is_enabled: boolean;
  }) =>
    request<any>(`/api/reminders/user/${userId}/${reminderId}`, {
      method: "PUT",
      body: JSON.stringify(data)
    }),

  // Adherence
  getCurrentAdherence: (userId: string) =>
    request<any>(`/api/adherence/user/${userId}/current`),

  getAdherenceHistory: (userId: string) =>
    request<any[]>(`/api/adherence/user/${userId}/history`),
};
export default api;
