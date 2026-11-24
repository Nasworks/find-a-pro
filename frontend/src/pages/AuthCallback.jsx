import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { PENDING_SIGNUP_KEY, afterSignupPath, ROLE_HOME } from './Signup';
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
        let u = res.data.user;
        localStorage.removeItem('dispatchr_pending_role');
        // Google sign-up: send the role-specific details collected before the redirect
        const pending = localStorage.getItem(PENDING_SIGNUP_KEY);
        if (pending && u.signup_complete === false) {
          try {
            const r = await api.post('/auth/complete-signup', JSON.parse(pending));
            u = r.data;
          } catch (e) { console.error('[AuthCallback] complete-signup failed:', e); }
        }
        localStorage.removeItem(PENDING_SIGNUP_KEY);
        setUser(u);
        if (u.signup_complete === false) { navigate('/signup', { replace: true }); return; }
        const isNew = !!pending;
        navigate(isNew ? afterSignupPath(u.role) : (ROLE_HOME[u.role] || '/client-home'), { replace: true, state: { user: u } });
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
