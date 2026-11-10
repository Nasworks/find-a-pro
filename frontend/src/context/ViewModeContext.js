import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

const ViewModeContext = createContext(null);

const STORAGE_KEY = 'dispatchr_view_mode';
// Below this width (phones + tablets) the app always uses the touch layout.
export const COMPACT_MAX = 1024;

function detectDefault() {
  if (typeof window === 'undefined') return 'desktop';
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'mobile' || stored === 'desktop') return stored;
  } catch { /* ignore */ }
  return window.innerWidth < 768 ? 'mobile' : 'desktop';
}

const inFrame = typeof window !== 'undefined' && window.self !== window.top;

export function ViewModeProvider({ children }) {
  const [mode, setMode] = useState(() => detectDefault());
  const [width, setWidth] = useState(() => (typeof window === 'undefined' ? 1280 : window.innerWidth));

  useEffect(() => {
    const onResize = () => setWidth(window.innerWidth);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const compact = width < COMPACT_MAX;

  useEffect(() => {
    if (!inFrame) {
      try { window.localStorage.setItem(STORAGE_KEY, mode); } catch { /* ignore */ }
    }
    const effective = compact ? 'mobile' : 'desktop';
    document.documentElement.setAttribute('data-view-mode', effective);
    document.documentElement.classList.toggle('view-mode-mobile', compact);
  }, [mode, compact]);

  const setViewMode = useCallback((next) => {
    if (next === 'mobile' || next === 'desktop') setMode(next);
  }, []);

  const toggle = useCallback(() => {
    setMode((prev) => (prev === 'mobile' ? 'desktop' : 'mobile'));
  }, []);

  // framed = desktop-size screen previewing the phone layout inside a device frame
  const framed = mode === 'mobile' && !compact && !inFrame;

  return (
    <ViewModeContext.Provider value={{ mode, isMobile: compact, compact, framed, inFrame, isDesktop: !compact, setViewMode, toggle }}>
      {children}
    </ViewModeContext.Provider>
  );
}

export function useViewMode() {
  const ctx = useContext(ViewModeContext);
  if (!ctx) throw new Error('useViewMode must be used within ViewModeProvider');
  return ctx;
}
