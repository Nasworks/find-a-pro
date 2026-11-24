import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Wrench, Building2, Shield, KeyRound, Landmark, ArrowRight, Loader2, Sparkles } from 'lucide-react';
import { Button } from '../components/ui/button';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import { toast } from 'sonner';
import ViewModeToggle from '../components/ViewModeToggle';
import Logo from '../components/Logo';
import { extractError } from '../lib/errors';

const roles = [
  { id: 'customer', title: 'Customer', desc: 'I need a service for my home', icon: User, iconBg: 'bg-blue-500' },
  { id: 'provider', title: 'Service Provider', desc: 'I offer trade services to clients', icon: Wrench, iconBg: 'bg-emerald-500' },
  { id: 'property', title: 'Property Manager', desc: 'Manage multiple properties and maintenance', icon: Building2, iconBg: 'bg-violet-500' },
  { id: 'landlord', title: 'Landlord', desc: 'Maintain rental properties and track spend', icon: KeyRound, iconBg: 'bg-orange-500' },
  { id: 'facilities', title: 'Facilities Management', desc: 'Apartment buildings, body corporates and shared spaces', icon: Landmark, iconBg: 'bg-slate-600' },
  { id: 'insurance', title: 'Insurance Partner', desc: 'Access shared property histories & docs', icon: Shield, iconBg: 'bg-teal-500' },
];

const ROLE_TO_PATH = {
  provider: '/provider/dashboard',
  property: '/property/dashboard',
  landlord: '/landlord/dashboard',
  facilities: '/facilities/dashboard',
  insurance: '/insurance/dashboard',
  customer: '/client-home',
};

export default function LandingRoleSelect() {
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();
  const { demoLogin } = useAuth();
  const [busy, setBusy] = useState(null);

  const enterAs = async (roleId) => {
    if (busy) return;
    setBusy(roleId);
    try {
      const u = await demoLogin(roleId);
      toast.success(`Welcome, ${u.name}!`);
      navigate(ROLE_TO_PATH[u.role] || '/client-home');
    } catch (err) {
      toast.error(extractError(err, 'Could not enter demo'));
      setBusy(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-accent/30">
      <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
        <Logo />
        <div className="flex items-center gap-2">
          <ViewModeToggle />
          <button onClick={toggle} className="text-sm text-muted-foreground hover:text-foreground px-3 py-1.5 rounded-lg hover:bg-accent transition-colors">
            {theme === 'dark' ? 'Light mode' : 'Dark mode'}
          </button>
          <Link to="/login">
            <Button variant="outline" data-testid="landing-login-btn">Log in</Button>
          </Link>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 pt-12 pb-24 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium mb-6">
          <Sparkles className="w-3.5 h-3.5" />
          Live preview · No signup required
        </div>
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight text-foreground leading-[1.05]">
          Your home or rental property,
          <span className="block bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
            managed intelligently.
          </span>
        </h1>
        <p className="mt-6 text-lg text-muted-foreground max-w-xl mx-auto">
          Pick an account type to explore Pro Finder NZ instantly — no email, no password.
        </p>

        <div className="mt-12 text-left space-y-3 max-w-xl mx-auto">
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Enter the preview as…</p>
          {roles.map((r) => {
            const Icon = r.icon;
            const isBusy = busy === r.id;
            return (
              <button
                key={r.id}
                data-testid={`role-select-${r.id}`}
                onClick={() => enterAs(r.id)}
                disabled={!!busy}
                className="w-full group flex items-center gap-4 p-4 rounded-2xl border border-border bg-card hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5 transition-all text-left disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <div className={`w-12 h-12 rounded-xl ${r.iconBg} flex items-center justify-center text-white shrink-0`}>
                  {isBusy ? <Loader2 className="w-6 h-6 animate-spin" /> : <Icon className="w-6 h-6" />}
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
          Prefer to log in?{' '}
          <Link to="/login" className="text-primary font-medium hover:underline">Use email or Google</Link>
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

