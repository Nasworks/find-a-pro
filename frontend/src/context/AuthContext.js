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
    } catch {
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

  const login = async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    localStorage.setItem('dispatchr_token', res.data.token);
    setUser(res.data.user);
    return res.data.user;
  };

  const register = async (payload) => {
    const res = await api.post('/auth/register', payload);
    localStorage.setItem('dispatchr_token', res.data.token);
    setUser(res.data.user);
    return res.data.user;
  };

  const logout = async () => {
    try { await api.post('/auth/logout'); } catch {}
    localStorage.removeItem('dispatchr_token');
    setUser(null);
  };

  const switchRole = async (role) => {
    await api.patch('/auth/role', { role });
    setUser((u) => ({ ...u, role }));
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, switchRole, refresh: checkAuth, setUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
