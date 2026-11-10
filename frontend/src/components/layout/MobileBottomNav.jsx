import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Home, Briefcase, MessageSquare, User, LayoutDashboard, ClipboardList, Wrench, KeyRound, Building2, Shield, Plus, Clock, Menu } from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../ui/sheet';
import Sidebar from './Sidebar';
import { useAuth } from '../../context/AuthContext';

const roleTabs = {
  customer: [
    { to: '/client-home', label: 'Home', icon: Home },
    { to: '/my-job-posts', label: 'Jobs', icon: Briefcase },
    { to: '/post-job', label: 'Post', icon: Plus, primary: true },
    { to: '/messages', label: 'Chat', icon: MessageSquare },
  ],
  provider: [
    { to: '/provider/dashboard', label: 'Home', icon: LayoutDashboard },
    { to: '/provider/job-board', label: 'Jobs', icon: ClipboardList },
    { to: '/provider/timesheet', label: 'Time', icon: Clock },
    { to: '/messages', label: 'Chat', icon: MessageSquare },
  ],
  property: [
    { to: '/property/dashboard', label: 'Home', icon: LayoutDashboard },
    { to: '/my-job-posts', label: 'Jobs', icon: Wrench },
    { to: '/post-job', label: 'Log', icon: Plus, primary: true },
    { to: '/messages', label: 'Chat', icon: MessageSquare },
  ],
  landlord: [
    { to: '/landlord/dashboard', label: 'Home', icon: KeyRound },
    { to: '/my-job-posts', label: 'Jobs', icon: Wrench },
    { to: '/post-job', label: 'Post', icon: Plus, primary: true },
    { to: '/messages', label: 'Chat', icon: MessageSquare },
  ],
  facilities: [
    { to: '/facilities/dashboard', label: 'Home', icon: Building2 },
    { to: '/my-job-posts', label: 'Tickets', icon: ClipboardList },
    { to: '/post-job', label: 'Log', icon: Plus, primary: true },
    { to: '/messages', label: 'Chat', icon: MessageSquare },
  ],
  insurance: [
    { to: '/insurance/dashboard', label: 'Home', icon: Shield },
    { to: '/messages', label: 'Chat', icon: MessageSquare },
    { to: '/profile', label: 'Me', icon: User },
  ],
};

export default function MobileBottomNav() {
  const { user } = useAuth();
  const tabs = roleTabs[user?.role] || roleTabs.customer;
  const [menuOpen, setMenuOpen] = useState(false);
  const cols = { 4: 'grid-cols-4', 5: 'grid-cols-5' }[tabs.length + 1] || 'grid-cols-5';

  return (
    <nav data-testid="mobile-bottom-nav" className="mobile-bottom-nav fixed bottom-0 inset-x-0 z-40 bg-card/95 backdrop-blur-xl border-t border-border">
      <div className={`grid ${cols} h-16 max-w-xl mx-auto px-1`}>
        {tabs.map((t) => <TabLink key={t.to} t={t} />)}
        <button
          data-testid="mobile-nav-menu"
          onClick={() => setMenuOpen(true)}
          className={`flex flex-col items-center justify-center gap-1 text-[11px] font-medium transition-colors ${menuOpen ? 'text-primary' : 'text-muted-foreground'}`}
        >
          <Menu className="w-5 h-5" />
          <span>Menu</span>
        </button>
      </div>
      <div className="h-[env(safe-area-inset-bottom)]" />
      <MenuSheet open={menuOpen} setOpen={setMenuOpen} user={user} />
    </nav>
  );
}

function TabLink({ t }) {
  const Icon = t.icon;
  return (
    <NavLink
      to={t.to}
      end
      data-testid={`mobile-nav-${t.label.toLowerCase()}`}
      className={({ isActive }) => `relative flex flex-col items-center justify-center gap-1 text-[11px] font-medium transition-colors ${t.primary ? 'text-foreground' : isActive ? 'text-primary' : 'text-muted-foreground'}`}
    >
      {({ isActive }) => (
        <>
          {!t.primary && isActive && <span className="absolute top-0 h-0.5 w-8 rounded-full bg-primary" />}
          {t.primary ? (
            <span className="w-12 h-12 -mt-5 rounded-2xl bg-primary flex items-center justify-center text-primary-foreground shadow-lg shadow-primary/30 ring-4 ring-background">
              <Icon className="w-5 h-5" />
            </span>
          ) : (
            <Icon className="w-5 h-5" />
          )}
          <span className={t.primary ? '-mt-0.5' : ''}>{t.label}</span>
        </>
      )}
    </NavLink>
  );
}

function MenuSheet({ open, setOpen, user }) {
  const { pathname } = useLocation();
  const initials = (user?.name || 'U').split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase();
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent side="left" className="w-[85vw] max-w-sm p-0 flex flex-col" data-testid="mobile-menu-sheet">
        <SheetHeader className="px-5 pt-5 pb-4 border-b border-border text-left">
          <SheetTitle className="sr-only">Menu</SheetTitle>
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-full bg-gradient-to-br from-primary to-blue-600 text-white text-sm font-semibold flex items-center justify-center shrink-0">{initials}</div>
            <div className="min-w-0">
              <div className="font-semibold text-foreground truncate">{user?.name}</div>
              <div className="text-xs text-muted-foreground capitalize truncate">{user?.role} · {pathname.split('/').filter(Boolean).pop()?.replace(/-/g, ' ') || 'home'}</div>
            </div>
          </div>
        </SheetHeader>
        <div className="flex-1 min-h-0 flex flex-col">
          <Sidebar collapsed={false} setCollapsed={() => {}} onNavigate={() => setOpen(false)} embedded />
        </div>
      </SheetContent>
    </Sheet>
  );
}
