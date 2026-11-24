import { useEffect, useRef, useState } from 'react';
import api from '../lib/api';

export const getPosition = () => new Promise((resolve, reject) => {
  if (!navigator.geolocation) return reject(new Error('This device has no location access'));
  navigator.geolocation.getCurrentPosition(
    (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
    () => reject(new Error('Allow location access to clock in or out')),
    { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 },
  );
});

// While enabled, sends the phone's location at most once a minute; the server starts/stops auto timesheets.
export function useGpsPings(enabled, onAction) {
  const [status, setStatus] = useState('off');
  const last = useRef(0);
  const cb = useRef(onAction);
  cb.current = onAction;

  useEffect(() => {
    if (!enabled || !navigator.geolocation) { setStatus(enabled ? 'unavailable' : 'off'); return undefined; }
    setStatus('waiting');
    const id = navigator.geolocation.watchPosition(async (p) => {
      setStatus('tracking');
      if (Date.now() - last.current < 60000) return;
      last.current = Date.now();
      try {
        const { data } = await api.post('/worker/location', { lat: p.coords.latitude, lng: p.coords.longitude });
        if (data.action) cb.current(data.action);
      } catch { /* next ping retries */ }
    }, () => setStatus('denied'), { enableHighAccuracy: true, maximumAge: 30000 });
    return () => navigator.geolocation.clearWatch(id);
  }, [enabled]);

  return status;
}
