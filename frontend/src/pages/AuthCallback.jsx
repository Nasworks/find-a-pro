import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const hash = window.location.hash || '';
    const params = new URLSearchParams(hash.replace(/^#/, ''));
    const sessionId = params.get('session_id');
    if (!sessionId) { navigate('/', { replace: true }); return; }

    const role = localStorage.getItem('dispatchr_pending_role') || localStorage.getItem('dispatchr_selected_role') || 'customer';

    (async () => {
      try {
        // Server sets httpOnly session_token cookie automatically (SameSite=None; Secure)
        const res = await api.post('/auth/session', { session_id: sessionId, role });
        setUser(res.data.user);
        localStorage.removeItem('dispatchr_pending_role');
        const u = res.data.user;
        const target =
          u.role === 'provider' ? '/provider/dashboard' :
          u.role === 'property' ? '/property/dashboard' :
          u.role === 'insurance' ? '/insurance/dashboard' : '/client-home';
        navigate(target, { replace: true, state: { user: u } });
      } catch (err) {
        console.error('[AuthCallback] session exchange failed:', err);
        navigate('/login', { replace: true });
      }
    })();
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-muted-foreground">Signing you in...</div>
    </div>
  );
}
