import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import api from '../lib/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const res = await api.get('/auth/me');
      setUser(res.data);
    } catch (err) {
      // 401 means not logged in — expected when there's no session
      if (err?.response?.status !== 401) {
        console.error('[AuthContext] /auth/me failed:', err);
      }
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // If returning from OAuth callback, skip /me check.
    if (window.location.hash?.includes('session_id=')) {
      setLoading(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const login = useCallback(async (email, password) => {
    // The server sets httpOnly `auth_token` cookie; no localStorage usage.
    const res = await api.post('/auth/login', { email, password });
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const register = useCallback(async (payload) => {
    const res = await api.post('/auth/register', payload);
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } catch (err) {
      console.error('[AuthContext] logout failed:', err);
    }
    setUser(null);
  }, []);

  const switchRole = useCallback(async (role) => {
    await api.patch('/auth/role', { role });
    setUser((u) => ({ ...u, role }));
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, switchRole, refresh: checkAuth, setUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
