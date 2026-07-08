import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { Loader2, User as UserIcon, Wrench, Building2, KeyRound, Shield, HardHat, Sparkles } from 'lucide-react';
import Logo from '../components/Logo';
import { extractError } from '../lib/errors';

const ROLE_TO_PATH = {
  provider: '/provider/dashboard',
  property: '/property/dashboard',
  landlord: '/landlord/dashboard',
  facilities: '/facilities/dashboard',
  insurance: '/insurance/dashboard',
  customer: '/client-home',
};

const DEMO_ROLES = [
  { id: 'customer',   label: 'Customer',       icon: UserIcon, color: 'bg-blue-500' },
  { id: 'provider',   label: 'Service Provider', icon: Wrench,   color: 'bg-emerald-500' },
  { id: 'property',   label: 'Property Manager', icon: Building2, color: 'bg-violet-500' },
  { id: 'landlord',   label: 'Landlord',       icon: KeyRound,  color: 'bg-orange-500' },
  { id: 'facilities', label: 'Facilities',     icon: HardHat,   color: 'bg-slate-600' },
  { id: 'insurance',  label: 'Insurance',      icon: Shield,    color: 'bg-teal-500' },
];

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [demoBusy, setDemoBusy] = useState(null);
  const { login, demoLogin } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const u = await login(email, password);
      toast.success(`Welcome back, ${u.name}!`);
      navigate(ROLE_TO_PATH[u.role] || '/client-home');
    } catch (err) {
      toast.error(extractError(err, 'Login failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/client-home';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const tryDemo = async (roleId) => {
    if (demoBusy) return;
    setDemoBusy(roleId);
    try {
      const u = await demoLogin(roleId);
      toast.success(`Signed in as ${u.name}`);
      navigate(ROLE_TO_PATH[u.role] || '/client-home');
    } catch (err) {
      toast.error(extractError(err, 'Demo login failed'));
    } finally {
      setDemoBusy(null);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-accent/30 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8"><Logo size="lg" /></div>

        {/* Demo login panel */}
        <div className="bg-card border border-primary/30 rounded-2xl p-5 mb-4 shadow-lg shadow-primary/5" data-testid="demo-login-panel">
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-primary bg-primary/10 border border-primary/20 rounded-full px-2 py-0.5">
              <Sparkles className="w-3 h-3" /> Preview
            </span>
            <h2 className="text-base font-semibold text-foreground">Try the app instantly</h2>
          </div>
          <p className="text-xs text-muted-foreground mb-3">One-click sign-in as any account type. No signup, no password.</p>
          <div className="grid grid-cols-2 gap-2">
            {DEMO_ROLES.map((r) => {
              const Icon = r.icon;
              const busy = demoBusy === r.id;
              return (
                <button
                  key={r.id}
                  type="button"
                  data-testid={`demo-login-${r.id}`}
                  onClick={() => tryDemo(r.id)}
                  disabled={!!demoBusy}
                  className="group flex items-center gap-2 p-2.5 rounded-xl border border-border hover:border-primary/40 hover:bg-accent/40 transition-all disabled:opacity-60 disabled:cursor-not-allowed text-left"
                >
                  <div className={`w-8 h-8 rounded-lg ${r.color} text-white flex items-center justify-center shrink-0`}>
                    {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Icon className="w-4 h-4" />}
                  </div>
                  <span className="text-xs font-medium text-foreground group-hover:text-primary transition-colors leading-tight">{r.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="bg-card border border-border rounded-2xl p-8 shadow-xl shadow-primary/5">
          <h1 className="text-2xl font-bold text-foreground">Welcome back</h1>
          <p className="text-muted-foreground text-sm mt-1">Log in to your Pro Finder NZ account</p>

          <button onClick={handleGoogle} type="button" className="mt-6 w-full flex items-center justify-center gap-3 py-2.5 rounded-lg border border-border hover:bg-accent transition-colors">
            <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            <span className="font-medium text-sm text-foreground">Continue with Google</span>
          </button>

          <div className="my-6 flex items-center gap-3"><div className="h-px bg-border flex-1" /><span className="text-xs text-muted-foreground">or</span><div className="h-px bg-border flex-1" /></div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required className="mt-1.5" />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Your password" required className="mt-1.5" />
            </div>
            <Button type="submit" disabled={loading} className="w-full h-11">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Log in'}
            </Button>
          </form>

          <p className="mt-6 text-sm text-muted-foreground text-center">
            New here? <Link to="/signup" className="text-primary font-medium hover:underline">Create account</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

