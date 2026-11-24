import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import Logo from '../components/Logo';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';

export default function JoinTeam() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(null);
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get(`/team/invites/${token}`).then((r) => { setInfo(r.data); setName(r.data.name || ''); })
      .catch((e) => setError(e.response?.data?.detail || 'This invite link is not valid'));
  }, [token]);

  const accept = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post(`/team/invites/${token}/accept`, { name, password });
      setUser(data.user);
      toast.success(`Welcome to ${info.company_name}!`);
      navigate('/worker/jobs', { replace: true });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not create your login');
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <div className="w-full max-w-md bg-card border border-border rounded-2xl p-6 space-y-5" data-testid="join-team-card">
        <Logo />
        {error && <p className="text-sm text-destructive" data-testid="join-error">{error}</p>}
        {!error && !info && <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />}
        {info && (
          <form onSubmit={accept} className="space-y-4">
            <div>
              <h1 className="text-xl font-bold text-foreground">Join {info.company_name}</h1>
              <p className="text-sm text-muted-foreground mt-1">Create your employee login for {info.email}.</p>
            </div>
            <div><Label>Your name</Label><Input value={name} onChange={(e) => setName(e.target.value)} className="mt-1.5" data-testid="join-name-input" /></div>
            <div><Label>Choose a password</Label><Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={6} className="mt-1.5" data-testid="join-password-input" /></div>
            <Button type="submit" className="w-full" disabled={busy || password.length < 6} data-testid="join-submit-btn">{busy && <Loader2 className="w-4 h-4 mr-2 animate-spin" />} Create login</Button>
            <p className="text-xs text-muted-foreground">Your company will see your timesheets and, while you're clocked in or auto timesheets are on, your location.</p>
          </form>
        )}
      </div>
    </div>
  );
}
