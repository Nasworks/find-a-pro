import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Home, Briefcase, MessageSquare, User, LayoutDashboard, ClipboardList, DollarSign, Wrench, KeyRound, Building2, Shield, Plus, MoreHorizontal, Clock, CalendarCheck } from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '../ui/sheet';
import { useAuth } from '../../context/AuthContext';

const roleTabs = {
  customer: [
    { to: '/client-home', label: 'Home', icon: Home },
    { to: '/my-job-posts', label: 'Jobs', icon: Briefcase },
    { to: '/post-job', label: 'Post', icon: Plus, primary: true },
    { to: '/messages', label: 'Chat', icon: MessageSquare },
    { to: '/bookings', label: 'Book', icon: CalendarCheck },
  ],
  provider: [
    { to: '/provider/dashboard', label: 'Home', icon: LayoutDashboard },
    { to: '/provider/job-board', label: 'Jobs', icon: ClipboardList },
    { to: '/provider/earnings', label: '$', icon: DollarSign },
    { to: '/messages', label: 'Chat', icon: MessageSquare },
    { to: '/provider/timesheet', label: 'Time', icon: Clock },
  ],
  property: [
    { to: '/property/dashboard', label: 'Home', icon: LayoutDashboard },
    { to: '/my-job-posts', label: 'Jobs', icon: Wrench },
    { to: '/post-job', label: 'Log', icon: Plus, primary: true },
    { to: '/messages', label: 'Chat', icon: MessageSquare },
    { to: '/bookings', label: 'Book', icon: Briefcase },
  ],
  landlord: [
    { to: '/landlord/dashboard', label: 'Home', icon: KeyRound },
    { to: '/my-job-posts', label: 'Jobs', icon: Wrench },
    { to: '/post-job', label: 'Post', icon: Plus, primary: true },
    { to: '/messages', label: 'Chat', icon: MessageSquare },
    { to: '/bookings', label: 'Book', icon: Briefcase },
  ],
  facilities: [
    { to: '/facilities/dashboard', label: 'Home', icon: Building2 },
    { to: '/my-job-posts', label: 'Tickets', icon: ClipboardList },
    { to: '/post-job', label: 'Log', icon: Plus, primary: true },
    { to: '/messages', label: 'Chat', icon: MessageSquare },
    { to: '/bookings', label: 'Book', icon: Briefcase },
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
  const [drawerOpen, setDrawerOpen] = useState(false);
  const totalCells = tabs.length + 1; // + More button
  const gridColsClass = { 3: 'grid-cols-3', 4: 'grid-cols-4', 5: 'grid-cols-5', 6: 'grid-cols-6' }[totalCells] || 'grid-cols-6';

  return (
    <>
      <nav data-testid="mobile-bottom-nav" className="fixed bottom-0 inset-x-0 z-40 bg-card/95 backdrop-blur border-t border-border">
        <div className={`grid ${gridColsClass} h-16 max-w-md mx-auto`}>
          {tabs.map((t) => {
            const Icon = t.icon;
            return (
              <NavLink
                key={t.to}
                to={t.to}
                end
                data-testid={`mobile-nav-${t.label.toLowerCase()}`}
                className={({ isActive }) => `flex flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors ${t.primary ? '' : isActive ? 'text-primary' : 'text-muted-foreground'}`}
              >
                {t.primary ? (
                  <span className="w-11 h-11 -mt-4 rounded-full bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center text-white shadow-lg shadow-primary/30">
                    <Icon className="w-5 h-5" />
                  </span>
                ) : (
                  <Icon className="w-5 h-5" />
                )}
                <span className={t.primary ? 'text-foreground -mt-0.5' : ''}>{t.label}</span>
              </NavLink>
            );
          })}
          {/* More sheet trigger */}
          <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
            <SheetTrigger asChild>
              <button data-testid="mobile-nav-more" className="flex flex-col items-center justify-center gap-0.5 text-[10px] font-medium text-muted-foreground transition-colors hover:text-primary">
                <MoreHorizontal className="w-5 h-5" />
                <span>More</span>
              </button>
            </SheetTrigger>
            <SheetContent side="bottom" className="rounded-t-2xl max-h-[80vh] overflow-y-auto">
              <SheetHeader>
                <SheetTitle>Quick access</SheetTitle>
              </SheetHeader>
              <MoreDrawerContent role={user?.role} onNavigate={() => setDrawerOpen(false)} />
            </SheetContent>
          </Sheet>
        </div>
        {/* Safe-area padding for iOS notch */}
        <div className="h-[env(safe-area-inset-bottom)]" />
      </nav>
    </>
  );
}

function MoreDrawerContent({ role, onNavigate }) {
  const navigate = useNavigate();
  const links = [
    { to: '/profile', label: 'Profile', icon: User },
    { to: '/find-providers', label: 'Find Providers', icon: Home },
    { to: '/cost-estimator', label: 'Cost Estimator', icon: DollarSign },
    { to: '/guide-help', label: 'Guide & Help', icon: Shield },
    { to: '/legal-privacy', label: 'Legal & Privacy', icon: Shield },
    { to: '/my-disputes', label: 'My Disputes', icon: Shield },
    { to: '/more', label: 'All modules', icon: MoreHorizontal },
  ];
  // Add role-specific quick links
  if (role === 'provider') links.unshift({ to: '/provider/calendar', label: 'Calendar', icon: ClipboardList });
  return (
    <div className="grid grid-cols-3 gap-2 py-4">
      {links.map((l) => {
        const Icon = l.icon;
        return (
          <button
            key={l.to}
            data-testid={`mobile-more-${l.to.replace(/\//g, '')}`}
            onClick={() => { navigate(l.to); onNavigate(); }}
            className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-muted hover:bg-accent transition-colors"
          >
            <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
              <Icon className="w-4 h-4" />
            </div>
            <span className="text-xs font-medium text-foreground text-center leading-tight">{l.label}</span>
          </button>
        );
      })}
    </div>
  );
}
