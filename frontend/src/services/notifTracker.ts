export function getNotifEventId(): string | null {
  const params = new URLSearchParams(window.location.search);
  return params.get('notifEventId');
}

export async function markActionCompleted(eventId: string) {
  try {
    await fetch(`/api/notifications/events/${eventId}/action-completed`, { method: 'POST' });
  } catch {
    // silently ignore
  }
}

export function clearNotifEventId() {
  const url = new URL(window.location.href);
  url.searchParams.delete('notifEventId');
  window.history.replaceState({}, '', url.toString());
}

export async function markLatestActionCompleted(userId: string, type: string) {
  try {
    await fetch(`/api/notifications/events/mark-latest-action/${userId}/${type}`, { method: 'POST' });
  } catch {
    // silently ignore
  }
}
