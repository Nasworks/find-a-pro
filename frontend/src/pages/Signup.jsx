import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import {
  Loader2, Home as HomeIcon, Wrench, Building2, KeyRound, Landmark, ShieldCheck, ArrowLeft, ArrowRight, Check,
} from 'lucide-react';
import Logo from '../components/Logo';
import { extractError } from '../lib/errors';
import api from '../lib/api';

export const PENDING_SIGNUP_KEY = 'pfnz_pending_signup';

export const ROLE_HOME = {
  provider: '/provider/dashboard', property: '/property/dashboard', landlord: '/landlord/dashboard',
  facilities: '/facilities/dashboard', insurance: '/insurance/dashboard', customer: '/client-home',
};
// Where a brand-new account goes first (providers continue to documents + specializations)
export const afterSignupPath = (role) => (role === 'provider' ? '/provider/verification?welcome=1' : ROLE_HOME[role] || '/client-home');

const ROLES = [
  { id: 'customer', title: 'Homeowner / Tenant', desc: 'I need work done at my home', icon: HomeIcon, color: 'bg-blue-500' },
  { id: 'provider', title: 'Service Provider', desc: 'I am a tradie or service business', icon: Wrench, color: 'bg-emerald-500' },
  { id: 'landlord', title: 'Landlord', desc: 'I own rental properties', icon: KeyRound, color: 'bg-amber-500' },
  { id: 'property', title: 'Property Manager', desc: 'I manage properties for owners', icon: Building2, color: 'bg-violet-500' },
  { id: 'facilities', title: 'Facilities Management', desc: 'Apartment buildings & body corporates', icon: Landmark, color: 'bg-slate-600' },
  { id: 'insurance', title: 'Insurance Partner', desc: 'I handle claims and repairs', icon: ShieldCheck, color: 'bg-rose-500' },
];

// Role-specific questions. `biz` = stored as business_name; others go into signup_details.
const FIELDS = {
  customer: [
    { k: 'home_type', l: 'Home type', type: 'choice', options: ['House', 'Apartment', 'Townhouse', 'Renting'] },
    { k: 'suburb', l: 'Suburb', ph: 'e.g. Ponsonby' },
  ],
  landlord: [
    { k: 'rental_count', l: 'How many rental properties?', type: 'choice', options: ['1', '2–5', '6–20', '20+'], required: true },
    { k: 'suburb', l: 'Main area', ph: 'e.g. North Shore' },
  ],
  property: [
    { k: 'biz', l: 'Company name', ph: 'e.g. Harbour Property Management', required: true },
    { k: 'properties_managed', l: 'Properties managed', type: 'choice', options: ['1–20', '21–100', '101–500', '500+'], required: true },
    { k: 'suburb', l: 'Main area', ph: 'e.g. Auckland Central' },
  ],
  facilities: [
    { k: 'biz', l: 'Organisation / building name', ph: 'e.g. Harbourview Body Corporate', required: true },
    { k: 'buildings_count', l: 'Buildings you look after', type: 'choice', options: ['1', '2–5', '6–20', '20+'], required: true },
    { k: 'suburb', l: 'Main area', ph: 'e.g. Newmarket' },
  ],
  insurance: [
    { k: 'biz', l: 'Company name', ph: 'e.g. Kiwi Home Insurance', required: true },
    { k: 'fsp_number', l: 'FSP registration number', ph: 'Optional — e.g. FSP123456' },
    { k: 'claims_per_month', l: 'Repair claims per month', type: 'choice', options: ['Under 10', '10–50', '50–200', '200+'] },
  ],
  provider: [
    { k: 'biz', l: 'Business name', ph: 'e.g. Kiwi Plumbing Ltd', required: true },
    { k: 'years_in_business', l: 'Years in business', type: 'choice', options: ['Under 1', '1–3', '4–10', '10+'], required: true },
    { k: 'nzbn', l: 'NZBN', ph: 'Optional — 13-digit NZ Business Number' },
    { k: 'trade_licence', l: 'Trade licence / registration number', ph: 'Optional — e.g. PGDB, EWRB or LBP number' },
    { k: 'suburb', l: 'Based in', ph: 'e.g. Mount Eden' },
  ],
};
const ACCOUNT_TYPE_ROLES = new Set(['customer', 'property', 'facilities']);

const GoogleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" /><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" /><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" /><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" /></svg>
);

export default function Signup() {
  const { user, register, setUser } = useAuth();
  const navigate = useNavigate();
  // A Google user who hasn't finished signup skips the login step
  const completing = !!user && user.signup_complete === false;
  const preselected = localStorage.getItem('dispatchr_selected_role');
  const [step, setStep] = useState(0);
  const [role, setRole] = useState(completing ? user.role : (ROLES.some((r) => r.id === preselected) ? preselected : ''));
  const [about, setAbout] = useState({ name: completing ? user.name || '' : '', phone: '', city: 'Auckland', account_type: 'residential' });
  const [details, setDetails] = useState({});
  const [login, setLogin] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  // Set once this page creates/completes the account, so the "already signed in" redirect doesn't override afterSignupPath
  const justSignedUp = useRef(false);

  useEffect(() => { if (user && user.signup_complete !== false && !justSignedUp.current) navigate(ROLE_HOME[user.role] || '/client-home', { replace: true }); }, [user, navigate]);

  const fields = useMemo(() => FIELDS[role] || [], [role]);
  const roleMeta = ROLES.find((r) => r.id === role);
  const steps = completing ? ['Account type', 'About you'] : ['Account type', 'About you', 'Create login'];
  const lastStep = steps.length - 1;

  const payload = () => {
    const sd = {};
    fields.forEach((f) => { if (f.k !== 'biz' && details[f.k]) sd[f.k] = details[f.k]; });
    return {
      role, name: about.name.trim(), phone: about.phone.trim() || null, city: about.city.trim() || null,
      account_type: ACCOUNT_TYPE_ROLES.has(role) ? about.account_type : role === 'provider' ? null : 'residential',
      business_name: details.biz?.trim() || null, signup_details: sd,
    };
  };

  const validStep = () => {
    if (step === 0) return !!role;
    if (step === 1) return about.name.trim() && fields.every((f) => !f.required || (details[f.k] || '').trim());
    return login.email.trim() && login.password.length >= 6;
  };

  const goNext = async () => {
    if (!validStep()) {
      toast.error(step === 0 ? 'Choose an account type' : step === 1 ? 'Please fill in the required fields' : 'Enter your email and a password of at least 6 characters');
      return;
    }
    if (step < lastStep) { setStep(step + 1); return; }
    if (completing) { await finishGoogle(); return; }
    setLoading(true);
    try {
      justSignedUp.current = true;
      const u = await register({ ...payload(), email: login.email.trim().toLowerCase(), password: login.password });
      toast.success(`Welcome to Pro Finder NZ, ${u.name}!`);
      navigate(afterSignupPath(u.role));
    } catch (err) {
      justSignedUp.current = false;
      toast.error(extractError(err, 'Signup failed'));
    } finally { setLoading(false); }
  };

  const finishGoogle = async () => {
    setLoading(true);
    try {
      const r = await api.post('/auth/complete-signup', payload());
      justSignedUp.current = true;
      setUser(r.data);
      localStorage.removeItem(PENDING_SIGNUP_KEY);
      toast.success(`Welcome to Pro Finder NZ, ${r.data.name}!`);
      navigate(afterSignupPath(r.data.role), { replace: true });
    } catch (err) {
      toast.error(extractError(err, 'Could not finish signup'));
    } finally { setLoading(false); }
  };

  const handleGoogle = () => {
    if (!(step === 1 ? validStep() : true)) { toast.error('Please fill in the required fields'); return; }
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    localStorage.setItem('dispatchr_pending_role', role);
    localStorage.setItem(PENDING_SIGNUP_KEY, JSON.stringify(payload()));
    const redirectUrl = window.location.origin + '/client-home';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-accent/30 px-4 py-10">
      <div className="w-full max-w-xl">
        <div className="flex justify-center mb-6"><Logo size="lg" /></div>
        <div className="bg-card border border-border rounded-2xl p-6 sm:p-8 shadow-xl shadow-primary/5" data-testid="signup-card">
          <div className="flex gap-2 mb-6" data-testid="signup-progress">
            {steps.map((s, i) => (
              <div key={s} className="flex-1">
                <div className={`h-1.5 rounded-full ${i <= step ? 'bg-primary' : 'bg-muted'}`} />
                <div className={`text-[11px] mt-1.5 ${i === step ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>{i + 1}. {s}</div>
              </div>
            ))}
          </div>

          {step === 0 && (
            <>
              <h1 className="text-2xl font-bold text-foreground">{completing ? 'Finish setting up your account' : 'Create your account'}</h1>
              <p className="text-muted-foreground text-sm mt-1">What best describes you? We&apos;ll tailor your signup.</p>
              <div className="grid sm:grid-cols-2 gap-2.5 mt-5">
                {ROLES.map((r) => {
                  const Icon = r.icon;
                  const on = role === r.id;
                  return (
                    <button key={r.id} type="button" data-testid={`signup-role-${r.id}`} aria-pressed={on} onClick={() => { setRole(r.id); setDetails({}); setAbout((a) => ({ ...a, account_type: r.id === 'facilities' ? 'commercial' : 'residential' })); }}
                      className={`relative flex items-center gap-3 p-3.5 rounded-xl border-2 text-left transition-colors ${on ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}>
                      <span className={`w-10 h-10 rounded-lg ${r.color} text-white flex items-center justify-center shrink-0`}><Icon className="w-5 h-5" /></span>
                      <span className="min-w-0">
                        <span className="block text-sm font-semibold text-foreground">{r.title}</span>
                        <span className="block text-xs text-muted-foreground">{r.desc}</span>
                      </span>
                      {on && <Check className="absolute top-2.5 right-2.5 w-4 h-4 text-primary" />}
                    </button>
                  );
                })}
              </div>
            </>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h1 className="text-2xl font-bold text-foreground">About you</h1>
                <p className="text-muted-foreground text-sm mt-1">{roleMeta?.title} account{role === 'provider' ? ' — you can upload qualifications and a police check next.' : ''}</p>
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                <div className="sm:col-span-2">
                  <Label>{role === 'provider' ? 'Your name' : 'Full name'}</Label>
                  <Input data-testid="signup-name" value={about.name} onChange={(e) => setAbout({ ...about, name: e.target.value })} placeholder="Jane Smith" className="mt-1.5" maxLength={80} />
                </div>
                <div>
                  <Label>Phone <span className="text-muted-foreground font-normal">(optional)</span></Label>
                  <Input data-testid="signup-phone" type="tel" value={about.phone} onChange={(e) => setAbout({ ...about, phone: e.target.value })} placeholder="021 123 4567" className="mt-1.5" />
                </div>
                <div>
                  <Label>City</Label>
                  <Input data-testid="signup-city" value={about.city} onChange={(e) => setAbout({ ...about, city: e.target.value })} className="mt-1.5" />
                </div>
              </div>
              {ACCOUNT_TYPE_ROLES.has(role) && (
                <div>
                  <Label>Account type</Label>
                  <div className="grid grid-cols-2 gap-2 mt-1.5">
                    {['residential', 'commercial'].map((t) => (
                      <button key={t} type="button" data-testid={`signup-account-${t}`} onClick={() => setAbout({ ...about, account_type: t })}
                        className={`p-2.5 rounded-lg border-2 text-sm font-medium capitalize ${about.account_type === t ? 'border-primary bg-primary/5 text-foreground' : 'border-border text-muted-foreground'}`}>{t}</button>
                    ))}
                  </div>
                </div>
              )}
              {fields.map((f) => (
                <div key={f.k}>
                  <Label>{f.l}{!f.required && f.type === 'choice' ? <span className="text-muted-foreground font-normal"> (optional)</span> : null}</Label>
                  {f.type === 'choice' ? (
                    <div className="flex flex-wrap gap-2 mt-1.5">
                      {f.options.map((o) => (
                        <button key={o} type="button" data-testid={`signup-${f.k}-${o}`} onClick={() => setDetails({ ...details, [f.k]: o })}
                          className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${details[f.k] === o ? 'bg-primary text-primary-foreground border-primary' : 'border-border text-muted-foreground hover:border-primary/40'}`}>{o}</button>
                      ))}
                    </div>
                  ) : (
                    <Input data-testid={`signup-${f.k}`} value={details[f.k] || ''} onChange={(e) => setDetails({ ...details, [f.k]: e.target.value })} placeholder={f.ph} className="mt-1.5" maxLength={120} />
                  )}
                </div>
              ))}
            </div>
          )}

          {step === 2 && !completing && (
            <div className="space-y-4">
              <div>
                <h1 className="text-2xl font-bold text-foreground">Create your login</h1>
                <p className="text-muted-foreground text-sm mt-1">Use your Google account or an email and password.</p>
              </div>
              <button onClick={handleGoogle} type="button" data-testid="signup-google" className="w-full flex items-center justify-center gap-3 py-2.5 rounded-lg border border-border hover:bg-accent transition-colors">
                <GoogleIcon /> <span className="font-medium text-sm text-foreground">Sign up with Google</span>
              </button>
              <div className="flex items-center gap-3 text-xs text-muted-foreground"><div className="flex-1 h-px bg-border" /> or <div className="flex-1 h-px bg-border" /></div>
              <div>
                <Label>Email</Label>
                <Input data-testid="signup-email" type="email" value={login.email} onChange={(e) => setLogin({ ...login, email: e.target.value })} placeholder="you@example.com" className="mt-1.5" autoComplete="email" />
              </div>
              <div>
                <Label>Password</Label>
                <Input data-testid="signup-password" type="password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })} placeholder="At least 6 characters" className="mt-1.5" autoComplete="new-password" onKeyDown={(e) => e.key === 'Enter' && goNext()} />
              </div>
            </div>
          )}

          <div className="flex items-center gap-3 mt-7">
            {step > 0 && <Button variant="outline" onClick={() => setStep(step - 1)} data-testid="signup-back"><ArrowLeft className="w-4 h-4 mr-1" /> Back</Button>}
            <Button className="flex-1" onClick={goNext} disabled={loading} data-testid="signup-next">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : step < lastStep ? <>Continue <ArrowRight className="w-4 h-4 ml-1" /></> : completing ? 'Finish' : 'Create account'}
            </Button>
          </div>
          {!completing && (
            <p className="text-sm text-muted-foreground text-center mt-6">
              Already have an account? <Link to="/login" className="text-primary font-medium hover:underline">Sign in</Link>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
