import React from 'react';
import { Link } from 'react-router-dom';
import { Calculator, BookOpen, Users, Scale, Flag, Gavel, Shield, Bell, Settings, Building2, Home as HomeIcon, ChevronRight } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const items = [
  { to: '/cost-estimator', icon: Calculator, label: 'Cost Estimator', desc: 'Median NZ market rates', color: 'bg-primary' },
  { to: '/guide-help', icon: BookOpen, label: 'Guide & Help', desc: 'FAQ, live chat, phone support', color: 'bg-emerald-500' },
  { to: '/community-forum', icon: Users, label: 'Community Forum', desc: 'Talk with 12,000+ NZ pros', color: 'bg-violet-500' },
  { to: '/legal-privacy', icon: Scale, label: 'Legal & Privacy', desc: 'ToS, Privacy, Warranty', color: 'bg-slate-500' },
  { to: '/report-provider', icon: Flag, label: 'Report Provider', desc: 'Report abuse or unsafe work', color: 'bg-rose-500' },
  { to: '/my-disputes', icon: Gavel, label: 'My Disputes', desc: 'Track mediation status', color: 'bg-amber-500' },
  { to: '/notifications', icon: Bell, label: 'Notifications', desc: 'Alerts and email preferences', color: 'bg-cyan-500' },
  { to: '/settings', icon: Settings, label: 'Settings', desc: 'Account, security, billing', color: 'bg-teal-500' },
];

export default function MoreMenu() {
  const { user } = useAuth();
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">More</h1>
        <p className="text-sm text-muted-foreground capitalize">Tools & resources · {user?.role} portal</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {items.map((it) => (
          <Link key={it.to} to={it.to} className="group flex items-center gap-3 p-4 bg-card border border-border rounded-2xl hover:border-primary/40 hover:shadow-md transition-all">
            <div className={`w-11 h-11 rounded-xl ${it.color} text-white flex items-center justify-center shrink-0`}><it.icon className="w-5 h-5" /></div>
            <div className="flex-1">
              <div className="font-semibold text-foreground">{it.label}</div>
              <div className="text-xs text-muted-foreground">{it.desc}</div>
            </div>
            <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
          </Link>
        ))}
      </div>
    </div>
  );
}
