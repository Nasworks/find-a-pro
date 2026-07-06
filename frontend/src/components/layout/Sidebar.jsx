import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Home, Briefcase, CalendarCheck, MessageSquare, User, Map, ShoppingBag, Newspaper, Plus, LogOut, ChevronLeft, ChevronRight, Sun, Moon, LayoutDashboard, ClipboardList, DollarSign, Calendar, Users, Building2, Shield, FileText, Wrench, Repeat, HardHat, Radio, History, Share2, Crown, ShieldCheck, LinkIcon, Locate, MoreHorizontal, Home as HomeIcon2, KeyRound } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { useCart } from '../../context/CartContext';
import Logo from '../Logo';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { User as UserIcon, Wrench as WrenchIcon, Building2 as B2, Shield as ShieldIcon } from 'lucide-react';
import { toast } from 'sonner';

const clientNav = [
  { section: 'Activity', items: [
    { to: '/client-home', label: 'Home', icon: Home },
    { to: '/my-job-posts', label: 'Job Posts & Bids', icon: Briefcase },
    { to: '/bookings', label: 'My Bookings', icon: CalendarCheck },
    { to: '/messages', label: 'Messages', icon: MessageSquare },
    { to: '/profile', label: 'Profile', icon: User },
  ]},
  { section: 'Explore', items: [
    { to: '/live-map', label: 'Live Map', icon: Map },
    { to: '/marketplace', label: 'Marketplace', icon: ShoppingBag },
    { to: '/news-feed', label: 'News Feed', icon: Newspaper },
    { to: '/community-forum', label: 'Forum', icon: Users },
  ]},
  { section: 'Actions', items: [
    { to: '/post-job', label: 'Post a Job', icon: Plus, highlight: true },
    { to: '/more', label: 'More', icon: MoreHorizontal },
  ]},
];

const providerNav = [
  { section: 'Workspace', items: [
    { to: '/provider/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/provider/job-board', label: 'Job Board', icon: ClipboardList },
    { to: '/provider/calendar', label: 'Calendar', icon: Calendar },
    { to: '/provider/earnings', label: 'Earnings', icon: DollarSign },
    { to: '/provider/quotations', label: 'Quotations', icon: FileText },
    { to: '/messages', label: 'Messages', icon: MessageSquare },
  ]},
  { section: 'Team & Ops', items: [
    { to: '/provider/team', label: 'Team', icon: Users },
    { to: '/provider/trades-board', label: 'Trades Board', icon: HardHat },
    { to: '/provider/external-jobs', label: 'External Jobs', icon: LinkIcon },
    { to: '/provider/track-workers', label: 'Track Workers', icon: Locate },
    { to: '/provider/gps-devices', label: 'GPS Devices', icon: Radio },
    { to: '/provider/job-history', label: 'Job History', icon: History },
  ]},
  { section: 'Grow', items: [
    { to: '/provider/trade-store', label: 'Trade Store', icon: ShoppingBag },
    { to: '/news-feed', label: 'News Feed', icon: Newspaper },
    { to: '/community-forum', label: 'Forum', icon: Users },
    { to: '/provider/referrals', label: 'Referrals', icon: Share2 },
    { to: '/provider/membership', label: 'Membership', icon: Crown },
    { to: '/provider/warranty-claims', label: 'Warranty Claims', icon: ShieldCheck },
    { to: '/profile', label: 'Profile', icon: User },
    { to: '/more', label: 'More', icon: MoreHorizontal },
  ]},
];

const propertyNav = [
  { section: 'Portfolio', items: [
    { to: '/property/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/my-job-posts', label: 'Maintenance Jobs', icon: Wrench },
    { to: '/bookings', label: 'Bookings', icon: CalendarCheck },
    { to: '/messages', label: 'Messages', icon: MessageSquare },
  ]},
  { section: 'Actions', items: [
    { to: '/post-job', label: 'Post a Job', icon: Plus, highlight: true },
    { to: '/marketplace', label: 'Marketplace', icon: ShoppingBag },
    { to: '/profile', label: 'Profile', icon: User },
    { to: '/more', label: 'More', icon: MoreHorizontal },
  ]},
];

const landlordNav = [
  { section: 'Rentals', items: [
    { to: '/landlord/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/property/dashboard', label: 'My Rentals', icon: HomeIcon2 },
    { to: '/my-job-posts', label: 'Maintenance', icon: Wrench },
    { to: '/bookings', label: 'Bookings', icon: CalendarCheck },
    { to: '/messages', label: 'Messages', icon: MessageSquare },
  ]},
  { section: 'Actions', items: [
    { to: '/post-job', label: 'Request Maintenance', icon: Plus, highlight: true },
    { to: '/cost-estimator', label: 'Cost Estimator', icon: DollarSign },
    { to: '/profile', label: 'Profile', icon: User },
    { to: '/more', label: 'More', icon: MoreHorizontal },
  ]},
];

const facilitiesNav = [
  { section: 'Portal', items: [
    { to: '/facilities/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/property/dashboard', label: 'Sites', icon: Building2 },
    { to: '/my-job-posts', label: 'SLA Tickets', icon: ClipboardList },
    { to: '/bookings', label: 'Bookings', icon: CalendarCheck },
    { to: '/messages', label: 'Messages', icon: MessageSquare },
  ]},
  { section: 'Actions', items: [
    { to: '/post-job', label: 'Log Ticket', icon: Plus, highlight: true },
    { to: '/cost-estimator', label: 'Cost Estimator', icon: DollarSign },
    { to: '/profile', label: 'Profile', icon: User },
    { to: '/more', label: 'More', icon: MoreHorizontal },
  ]},
];

const insuranceNav = [
  { section: 'Portal', items: [
    { to: '/insurance/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/messages', label: 'Messages', icon: MessageSquare },
    { to: '/profile', label: 'Profile', icon: User },
    { to: '/more', label: 'More', icon: MoreHorizontal },
  ]},
];

const roleNav = { customer: clientNav, provider: providerNav, property: propertyNav, insurance: insuranceNav, landlord: landlordNav, facilities: facilitiesNav };

const roles = [
  { id: 'customer', label: 'Customer', icon: UserIcon, color: 'bg-blue-500' },
  { id: 'provider', label: 'Service Provider', icon: WrenchIcon, color: 'bg-emerald-500' },
  { id: 'property', label: 'Property Manager', icon: B2, color: 'bg-violet-500' },
  { id: 'landlord', label: 'Landlord', icon: KeyRound, color: 'bg-orange-500' },
  { id: 'facilities', label: 'Facilities Management', icon: Building2, color: 'bg-slate-600' },
  { id: 'insurance', label: 'Insurance', icon: ShieldIcon, color: 'bg-teal-500' },
];

export default function Sidebar({ collapsed, setCollapsed }) {
  const { user, logout, switchRole } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const nav = roleNav[user?.role] || clientNav;
  const [switchOpen, setSwitchOpen] = React.useState(false);

  const handleSwitchRole = async (roleId) => {
    if (roleId === user.role) { setSwitchOpen(false); return; }
    try {
      await switchRole(roleId);
      toast.success(`Switched to ${roleId}`);
      const target = roleId === 'provider' ? '/provider/dashboard'
        : roleId === 'property' ? '/property/dashboard'
        : roleId === 'landlord' ? '/landlord/dashboard'
        : roleId === 'facilities' ? '/facilities/dashboard'
        : roleId === 'insurance' ? '/insurance/dashboard'
        : '/client-home';
      setSwitchOpen(false);
      navigate(target);
    } catch { toast.error('Failed to switch role'); }
  };

  const doLogout = async () => { await logout(); navigate('/'); };

  return (
    <aside className={`${collapsed ? 'w-16' : 'w-64'} shrink-0 border-r border-border bg-card flex flex-col transition-all duration-200 sticky top-0 h-screen`}>
      <div className="h-16 px-4 border-b border-border flex items-center justify-between">
        {collapsed ? (
          <div className="mx-auto"><Logo showText={false} size="sm" /></div>
        ) : (
          <Logo />
        )}
        <button onClick={() => setCollapsed(!collapsed)} className={`text-muted-foreground hover:text-foreground p-1 rounded-md hover:bg-accent ${collapsed ? 'hidden' : ''}`}>
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>
      {collapsed && (
        <button onClick={() => setCollapsed(false)} className="mx-auto mt-2 text-muted-foreground hover:text-foreground p-1 rounded-md hover:bg-accent">
          <ChevronRight className="w-4 h-4" />
        </button>
      )}

      <nav className="flex-1 overflow-y-auto scrollbar-thin py-4 px-2">
        {nav.map((sec) => (
          <div key={sec.section} className="mb-4">
            {!collapsed && <div className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{sec.section}</div>}
            <div className="space-y-0.5">
              {sec.items.map((it) => (
                <NavLink key={it.to} to={it.to} data-testid={`sidebar-nav-${it.label.toLowerCase().replace(/\s+&\s+/g, '-').replace(/\s+/g, '-')}`} className={({ isActive }) => `group flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${it.highlight ? 'bg-primary text-primary-foreground hover:bg-primary/90 justify-center shadow-sm shadow-primary/20' : isActive ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-foreground hover:bg-accent'}`}>
                  <it.icon className="w-4 h-4 shrink-0" />
                  {!collapsed && <span className="truncate">{it.label}</span>}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-border p-2 space-y-1">
        <Dialog open={switchOpen} onOpenChange={setSwitchOpen}>
          <DialogTrigger asChild>
            <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
              <Repeat className="w-4 h-4 shrink-0" />
              {!collapsed && <span>Switch Account Type</span>}
            </button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Switch account type</DialogTitle></DialogHeader>
            <div className="space-y-2 mt-4">
              {roles.map((r) => {
                const Icon = r.icon;
                const active = r.id === user?.role;
                return (
                  <button key={r.id} data-testid={`switch-role-${r.id}`} onClick={() => handleSwitchRole(r.id)} className={`w-full flex items-center gap-3 p-3 rounded-xl border ${active ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'} transition-colors text-left`}>
                    <div className={`w-10 h-10 rounded-lg ${r.color} flex items-center justify-center text-white`}><Icon className="w-5 h-5" /></div>
                    <div className="flex-1">
                      <div className="font-medium text-foreground">{r.label}</div>
                    </div>
                    {active && <span className="text-xs text-primary font-medium">Current</span>}
                  </button>
                );
              })}
            </div>
          </DialogContent>
        </Dialog>

        <button onClick={toggle} className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          {!collapsed && <span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>}
        </button>

        <button onClick={doLogout} className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors">
          <LogOut className="w-4 h-4" />
          {!collapsed && <span>Log out</span>}
        </button>
      </div>
    </aside>
  );
}
