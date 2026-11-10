import React, { useRef, useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Bell, Monitor } from 'lucide-react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import MobileBottomNav from './MobileBottomNav';
import Logo from '../Logo';
import { useViewMode } from '../../context/ViewModeContext';
import { useAuth } from '../../context/AuthContext';

export default function MainLayout() {
  const { compact, framed } = useViewMode();
  if (framed) return <PhoneFrame />;
  return compact ? <MobileLayout /> : <DesktopLayout />;
}

function DesktopLayout() {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-x-hidden">
          <div className="animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

function MobileLayout() {
  return (
    <div className="mobile-viewport-inner" data-testid="mobile-shell">
      <MobileTopBar />
      <main className="flex-1 min-w-0 overflow-x-hidden pb-24">
        <div className="animate-fade-in min-w-0">
          <Outlet />
        </div>
      </main>
      <MobileBottomNav />
    </div>
  );
}

function MobileTopBar() {
  const { user } = useAuth();
  const initials = (user?.name || 'U').split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase();
  return (
    <header className="sticky top-0 z-30 h-14 bg-card/95 backdrop-blur border-b border-border flex items-center justify-between px-4">
      <Logo />
      <div className="flex items-center gap-1">
        <button className="w-10 h-10 rounded-full hover:bg-accent flex items-center justify-center relative" aria-label="Notifications" data-testid="mobile-notifications-btn">
          <Bell className="w-5 h-5 text-muted-foreground" />
          <span className="absolute top-2.5 right-2.5 w-2 h-2 rounded-full bg-primary" />
        </button>
        <Link to="/profile" data-testid="mobile-avatar-link" className="w-9 h-9 rounded-full bg-gradient-to-br from-primary to-blue-600 text-white text-xs font-semibold flex items-center justify-center">{initials}</Link>
      </div>
    </header>
  );
}

function PhoneFrame() {
  const loc = useLocation();
  const navigate = useNavigate();
  const { setViewMode } = useViewMode();
  const frameRef = useRef(null);
  const [src] = useState(loc.pathname + loc.search);

  const exit = () => {
    try {
      const l = frameRef.current.contentWindow.location;
      navigate(l.pathname + l.search, { replace: true });
    } catch { /* ignore */ }
    setViewMode('desktop');
  };

  return (
    <div className="phone-stage" data-testid="phone-frame-stage">
      <div className="phone-device">
        <iframe ref={frameRef} src={src} title="Mobile preview" data-testid="mobile-preview-frame" className="w-full h-full border-0" />
      </div>
      <div className="phone-stage-side">
        <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Mobile preview</div>
        <p className="text-sm text-muted-foreground max-w-[220px]">This is exactly how the app looks on a phone.</p>
        <button onClick={exit} data-testid="exit-mobile-preview" className="mt-2 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity">
          <Monitor className="w-4 h-4" /> Back to desktop
        </button>
      </div>
    </div>
  );
}
