import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

const ViewModeContext = createContext(null);

const STORAGE_KEY = 'dispatchr_view_mode';

function detectDefault() {
  if (typeof window === 'undefined') return 'desktop';
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'mobile' || stored === 'desktop') return stored;
  } catch { /* ignore */ }
  // Auto: use mobile if the physical viewport is under 768px
  return window.innerWidth < 768 ? 'mobile' : 'desktop';
}

export function ViewModeProvider({ children }) {
  const [mode, setMode] = useState(() => detectDefault());

  useEffect(() => {
    if (!mode) return;
    try { window.localStorage.setItem(STORAGE_KEY, mode); } catch { /* ignore */ }
    // Also mirror onto <html> for CSS-based tweaks if desired
    document.documentElement.setAttribute('data-view-mode', mode);
    if (mode === 'mobile') document.documentElement.classList.add('view-mode-mobile');
    else document.documentElement.classList.remove('view-mode-mobile');
  }, [mode]);

  const setViewMode = useCallback((next) => {
    if (next === 'mobile' || next === 'desktop') setMode(next);
  }, []);

  const toggle = useCallback(() => {
    setMode((prev) => (prev === 'mobile' ? 'desktop' : 'mobile'));
  }, []);

  return (
    <ViewModeContext.Provider value={{ mode, isMobile: mode === 'mobile', isDesktop: mode === 'desktop', setViewMode, toggle }}>
      {children}
    </ViewModeContext.Provider>
  );
}

export function useViewMode() {
  const ctx = useContext(ViewModeContext);
  if (!ctx) throw new Error('useViewMode must be used within ViewModeProvider');
  return ctx;
}
