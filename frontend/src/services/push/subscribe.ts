import api from '../api/client';

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  return new Uint8Array([...rawData].map(c => c.charCodeAt(0)));
}

export async function subscribeToPush(userId: string): Promise<boolean> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    console.warn('Push not supported');
    return false;
  }

  const perm = await Notification.requestPermission();
  if (perm !== 'granted') return false;

  const { publicKey } = await api.getVapidPublicKey();
  const reg = await navigator.serviceWorker.register('/sw.js');
  await navigator.serviceWorker.ready;

  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey) as BufferSource,
  });

  const subJSON = sub.toJSON();
  await api.subscribePush(userId, {
    endpoint: subJSON.endpoint!,
    p256dh_key: subJSON.keys!.p256dh,
    auth_key: subJSON.keys!.auth,
    device_type: /mobile|tablet/i.test(navigator.userAgent) ? 'mobile' : 'desktop',
  });

  return true;
}

export async function unsubscribeFromPush(userId: string): Promise<boolean> {
  try {
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (!sub) return true;
    await api.unsubscribePush(userId, sub.endpoint);
    await sub.unsubscribe();
    return true;
  } catch {
    return false;
  }
}

export async function getPushSubscriptionStatus(): Promise<'granted' | 'denied' | 'prompt'> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return 'denied';
  return Notification.permission as 'granted' | 'denied' | 'prompt';
}
