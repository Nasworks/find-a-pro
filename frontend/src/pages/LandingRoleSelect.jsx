import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Wrench, Building2, Shield, ArrowRight, ChevronDown } from 'lucide-react';
import { Button } from '../components/ui/button';
import { useTheme } from '../context/ThemeContext';
import Logo from '../components/Logo';

const roles = [
  { id: 'customer', title: 'Customer', desc: 'I need a service for my home or business', icon: User, color: 'from-blue-500 to-blue-600', bg: 'bg-blue-50 dark:bg-blue-950/40', iconBg: 'bg-blue-500' },
  { id: 'provider', title: 'Service Provider', desc: 'I offer trade services to clients', icon: Wrench, color: 'from-emerald-500 to-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-950/40', iconBg: 'bg-emerald-500' },
  { id: 'property', title: 'Property Manager', desc: 'Manage multiple properties and maintenance', icon: Building2, color: 'from-violet-500 to-violet-600', bg: 'bg-violet-50 dark:bg-violet-950/40', iconBg: 'bg-violet-500' },
  { id: 'insurance', title: 'Insurance Partner', desc: 'Access shared property histories & docs', icon: Shield, color: 'from-teal-500 to-teal-600', bg: 'bg-teal-50 dark:bg-teal-950/40', iconBg: 'bg-teal-500' },
];

export default function LandingRoleSelect() {
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();

  const handleRole = (roleId) => {
    localStorage.setItem('dispatchr_selected_role', roleId);
    navigate('/signup');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-accent/30">
      <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
        <Logo />
        <div className="flex items-center gap-3">
          <button onClick={toggle} className="text-sm text-muted-foreground hover:text-foreground px-3 py-1.5 rounded-lg hover:bg-accent transition-colors">
            {theme === 'dark' ? 'Light mode' : 'Dark mode'}
          </button>
          <Link to="/login">
            <Button variant="outline">Log in</Button>
          </Link>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 pt-12 pb-24 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-primary pulse-dot" />
          Trusted by 12,000+ homes across NZ
        </div>
        <h1 className="text-5xl md:text-6xl font-bold tracking-tight text-foreground">
          Your home,
          <span className="block bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
            managed intelligently.
          </span>
        </h1>
        <p className="mt-6 text-lg text-muted-foreground max-w-xl mx-auto">
          Describe what you need — we'll instantly match you with a verified, top-rated local professional.
        </p>

        <div className="mt-12 text-left space-y-3 max-w-xl mx-auto">
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Choose your account type</p>
          {roles.map((r) => {
            const Icon = r.icon;
            return (
              <button
                key={r.id}
                onClick={() => handleRole(r.id)}
                className="w-full group flex items-center gap-4 p-4 rounded-2xl border border-border bg-card hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5 transition-all text-left"
              >
                <div className={`w-12 h-12 rounded-xl ${r.iconBg} flex items-center justify-center text-white shrink-0`}>
                  <Icon className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <div className="font-semibold text-foreground">{r.title}</div>
                  <div className="text-sm text-muted-foreground">{r.desc}</div>
                </div>
                <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </button>
            );
          })}
        </div>

        <p className="mt-8 text-sm text-muted-foreground">
          Already a member?{' '}
          <Link to="/login" className="text-primary font-medium hover:underline">Log in</Link>
        </p>
      </div>

      <div className="border-t border-border">
        <div className="max-w-6xl mx-auto px-6 py-8 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            {n: '12k+', l: 'Verified pros'},
            {n: '58k+', l: 'Jobs completed'},
            {n: '4.8★', l: 'Avg rating'},
            {n: '24/7', l: 'Emergency dispatch'},
          ].map((s) => (
            <div key={s.l}>
              <div className="text-2xl font-bold text-foreground">{s.n}</div>
              <div className="text-xs text-muted-foreground mt-1">{s.l}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
