import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, Briefcase, CalendarCheck, MessageSquare, User, Map, ShoppingBag, Newspaper, Plus, ChevronLeft, ChevronRight, LayoutDashboard, ClipboardList, DollarSign, Calendar, Users, Building2, FileText, Wrench, History, Share2, ShieldCheck, LinkIcon, Locate, MoreHorizontal, Home as HomeIcon2, KeyRound, Heart, Clock } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import Logo from '../Logo';
import { User as UserIcon, Wrench as WrenchIcon, Building2 as B2, Shield as ShieldIcon } from 'lucide-react';
import SidebarNavSection from './SidebarNavSection';
import SidebarFooter from './SidebarFooter';

const clientNav = [
  { section: 'Activity', items: [
    { to: '/client-home', label: 'Home', icon: Home },
    { to: '/my-job-posts', label: 'Job Posts & Bids', icon: Briefcase },
    { to: '/bookings', label: 'My Bookings', icon: CalendarCheck },
    { to: '/messages', label: 'Messages', icon: MessageSquare },
    { to: '/tenancies', label: 'My Property Link', icon: KeyRound },
    { to: '/profile', label: 'Profile', icon: User },
  ]},
  { section: 'Explore', items: [
    { to: '/find-providers', label: 'Find Providers', icon: Users },
    { to: '/saved-providers', label: 'Saved Pros', icon: Heart },
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
    { to: '/provider/timesheet', label: 'Timesheet', icon: Clock },
    { to: '/messages', label: 'Messages', icon: MessageSquare },
  ]},
  { section: 'Team & Ops', items: [
    { to: '/provider/team', label: 'Team', icon: Users },
    { to: '/provider/external-jobs', label: 'External Jobs', icon: LinkIcon },
    { to: '/provider/track-workers', label: 'Track Workers', icon: Locate },
    { to: '/provider/job-history', label: 'Job History', icon: History },
  ]},
  { section: 'Grow', items: [
    { to: '/provider/referrals', label: 'Referrals', icon: Share2 },
    { to: '/profile', label: 'Profile', icon: User },
    { to: '/more', label: 'More', icon: MoreHorizontal },
  ]},
];

const propertyNav = [
  { section: 'Portfolio', items: [
    { to: '/property/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/approvals', label: 'Approval Queue', icon: ShieldCheck },
    { to: '/tenancies', label: 'Tenant Requests', icon: Users },
    { to: '/my-job-posts', label: 'Maintenance Jobs', icon: Wrench },
    { to: '/bookings', label: 'Bookings', icon: CalendarCheck },
    { to: '/messages', label: 'Messages', icon: MessageSquare },
  ]},
  { section: 'Actions', items: [
    { to: '/post-job', label: 'Post a Job', icon: Plus, highlight: true },
    { to: '/find-providers', label: 'Find Providers', icon: Users },
    { to: '/saved-providers', label: 'Saved Pros', icon: Heart },
    { to: '/marketplace', label: 'Marketplace', icon: ShoppingBag },
    { to: '/profile', label: 'Profile', icon: User },
    { to: '/more', label: 'More', icon: MoreHorizontal },
  ]},
];

const landlordNav = [
  { section: 'Rentals', items: [
    { to: '/landlord/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/approvals', label: 'Approval Queue', icon: ShieldCheck },
    { to: '/tenancies', label: 'My Tenants', icon: Users },
    { to: '/property/dashboard', label: 'My Rentals', icon: HomeIcon2 },
    { to: '/my-job-posts', label: 'Maintenance', icon: Wrench },
    { to: '/bookings', label: 'Bookings', icon: CalendarCheck },
    { to: '/messages', label: 'Messages', icon: MessageSquare },
  ]},
  { section: 'Actions', items: [
    { to: '/post-job', label: 'Request Maintenance', icon: Plus, highlight: true },
    { to: '/find-providers', label: 'Find Providers', icon: Users },
    { to: '/saved-providers', label: 'Saved Pros', icon: Heart },
    { to: '/cost-estimator', label: 'Cost Estimator', icon: DollarSign },
    { to: '/profile', label: 'Profile', icon: User },
    { to: '/more', label: 'More', icon: MoreHorizontal },
  ]},
];

const facilitiesNav = [
  { section: 'Portal', items: [
    { to: '/facilities/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/approvals', label: 'Approval Queue', icon: ShieldCheck },
    { to: '/tenancies', label: 'Tenant Requests', icon: Users },
    { to: '/property/dashboard', label: 'Sites', icon: Building2 },
    { to: '/my-job-posts', label: 'SLA Tickets', icon: ClipboardList },
    { to: '/bookings', label: 'Bookings', icon: CalendarCheck },
    { to: '/messages', label: 'Messages', icon: MessageSquare },
  ]},
  { section: 'Actions', items: [
    { to: '/post-job', label: 'Log Ticket', icon: Plus, highlight: true },
    { to: '/find-providers', label: 'Find Providers', icon: Users },
    { to: '/saved-providers', label: 'Saved Pros', icon: Heart },
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

export default function Sidebar({ collapsed, setCollapsed, embedded = false, onNavigate }) {
  const { user } = useAuth();
  const nav = roleNav[user?.role] || clientNav;

  return (
    <aside className={`${embedded ? 'w-full h-full flex-1' : `${collapsed ? 'w-16' : 'w-64'} sticky top-0 h-screen`} shrink-0 border-r border-border bg-card flex flex-col transition-all duration-200`}>
      {!embedded && (
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
      )}
      {!embedded && collapsed && (
        <button onClick={() => setCollapsed(false)} className="mx-auto mt-2 text-muted-foreground hover:text-foreground p-1 rounded-md hover:bg-accent">
          <ChevronRight className="w-4 h-4" />
        </button>
      )}

      <nav className="flex-1 overflow-y-auto scrollbar-thin py-4 px-2">
        {nav.map((sec) => (
          <SidebarNavSection
            key={sec.section}
            section={sec.section}
            items={sec.items}
            collapsed={collapsed}
            onNavigate={onNavigate}
          />
        ))}
      </nav>

      <SidebarFooter collapsed={collapsed} roles={roles} />
    </aside>
  );
}
