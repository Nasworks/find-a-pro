import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Zap, Users, Package, TrendingUp, ClipboardList, DollarSign, Star, ShieldCheck, ChevronRight, Clock } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'sonner';

export default function ProviderDashboard() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [stats, setStats] = useState({});
  const [jobs, setJobs] = useState([]);

  const load = useCallback(async () => {
    try {
      const [p, s, j] = await Promise.all([
        api.get('/providers/me').catch(() => ({ data: null })),
        api.get('/stats/provider').catch(() => ({ data: {} })),
        api.get('/jobs/board').catch(() => ({ data: [] })),
      ]);
      setProfile(p.data);
      setStats(s.data);
      setJobs(j.data.slice(0, 5));
    } catch (err) {
      console.error('[ProviderDashboard] load failed:', err);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggleOnline = async () => {
    const newState = !profile?.online;
    await api.patch('/providers/me', { online: newState });
    setProfile({ ...profile, online: newState });
    toast.success(newState ? 'You are online 🟢' : 'You are offline');
  };

  const initials = (user?.name || 'U').split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase();

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="bg-card border border-border rounded-2xl p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary to-blue-600 text-white font-bold text-lg flex items-center justify-center">{initials}</div>
            <div>
              <div className="text-xs text-muted-foreground">Provider Portal</div>
              <div className="text-2xl font-bold text-foreground">Welcome back, {user?.name?.split(' ')[0]}</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm">
              <span className={`w-2.5 h-2.5 rounded-full ${profile?.online ? 'bg-emerald-500' : 'bg-muted-foreground'}`} />
              <span className="text-muted-foreground">{profile?.online ? 'Currently Online' : 'Currently Offline'}</span>
            </div>
            <Button onClick={toggleOnline} variant={profile?.online ? 'outline' : 'default'}>{profile?.online ? 'Go Offline' : 'Go Online'}</Button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-6">
          <QuickAction icon={ShieldCheck} title="Verify" desc="Qualifications" color="bg-teal-500" />
          <QuickAction icon={Users} title="Team" desc="Manage workers" color="bg-violet-500" />
          <QuickAction icon={Clock} title="Timesheet" desc="Track your time" color="bg-amber-500" to="/provider/timesheet" />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon={DollarSign} label="Earnings" value={`$${Math.round(stats.earnings || 0)}`} color="text-emerald-500" />
        <StatCard icon={ClipboardList} label="Active Jobs" value={stats.active_jobs || 0} color="text-primary" />
        <StatCard icon={TrendingUp} label="Completed" value={stats.jobs_done || 0} color="text-violet-500" />
        <StatCard icon={Zap} label="Pending Bids" value={stats.pending_bids || 0} color="text-amber-500" />
      </div>

      <div className="bg-gradient-to-r from-primary to-blue-600 rounded-2xl p-5 text-white">
        <div className="flex items-center gap-2 text-xs font-medium opacity-90"><Star className="w-3.5 h-3.5" /> No active plan</div>
        <div className="font-semibold mt-1">Subscribe to get listed and receive job leads</div>
        <div className="text-sm opacity-90">Pro plan: unlimited bids, priority placement, verified badge.</div>
        <Button variant="secondary" className="mt-4 bg-white/20 hover:bg-white/30 text-white border-0">Explore Plans</Button>
      </div>

      <div className="bg-card border border-border rounded-2xl p-5">
        <div className="font-semibold text-foreground mb-4">Pricing Intelligence</div>
        <div className="flex items-baseline justify-between">
          <div>
            <div className="text-xs text-muted-foreground">Your current rate</div>
            <div className="text-3xl font-bold text-foreground">${profile?.hourly_rate || 85}<span className="text-sm font-normal text-muted-foreground">/hr</span></div>
          </div>
          <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">Market Leader</Badge>
        </div>
        <div className="mt-3 text-xs text-muted-foreground">Higher than 70% of nearby pros</div>
        <div className="mt-2 h-2 rounded-full bg-muted overflow-hidden">
          <div className="h-full bg-gradient-to-r from-primary to-blue-600" style={{ width: '70%' }} />
        </div>
        <div className="flex justify-between text-[10px] text-muted-foreground mt-1"><span>$75</span><span>$95</span></div>

        <div className="mt-6 space-y-2">
          <div className="text-xs uppercase font-semibold text-muted-foreground">Guidance by Job Type</div>
          {[
            { l: 'Emergency Repair', p: '$120/hr', tag: 'High Demand', c: 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300' },
            { l: 'Standard Maintenance', p: '$75/hr', tag: 'Medium Demand', c: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300' },
            { l: 'Installation', p: '$90/hr', tag: 'Very High Demand', c: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300' },
          ].map((g) => (
            <div key={g.l} className="flex items-center justify-between p-3 rounded-lg bg-muted/40">
              <div>
                <div className="text-sm font-medium text-foreground">{g.l}</div>
                <div className="text-xs text-muted-foreground">Avg market rate: {g.p}</div>
              </div>
              <Badge className={g.c}>{g.tag}</Badge>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-foreground">Fresh jobs on the board</h2>
          <Link to="/provider/job-board" className="text-sm text-primary hover:underline">View all</Link>
        </div>
        <div className="space-y-2">
          {jobs.map((j) => (
            <Link to={`/jobs/${j.job_id}`} key={j.job_id} className="block bg-card border border-border rounded-xl p-4 hover:border-primary/40 transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-foreground">{j.title}</div>
                  <div className="text-xs text-muted-foreground line-clamp-1">{j.description}</div>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground mt-2">
                <span className="capitalize">{j.category}</span>
                <span>· {j.location}</span>
                {j.budget_min && <span>· ${j.budget_min}–{j.budget_max}</span>}
              </div>
            </Link>
          ))}
          {jobs.length === 0 && <div className="text-sm text-muted-foreground text-center py-8">No open jobs right now</div>}
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-card border border-border rounded-2xl p-4">
      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className={`w-8 h-8 rounded-lg bg-muted/60 flex items-center justify-center ${color}`}><Icon className="w-4 h-4" /></div>
      </div>
      <div className="text-2xl font-bold text-foreground mt-2">{value}</div>
    </div>
  );
}

function QuickAction({ icon: Icon, title, desc, color, to }) {
  const content = (
    <div className="bg-muted/40 hover:bg-muted rounded-xl p-3 flex items-center gap-3 transition-colors cursor-pointer">
      <div className={`w-9 h-9 rounded-lg ${color} text-white flex items-center justify-center`}><Icon className="w-4 h-4" /></div>
      <div>
        <div className="text-sm font-medium text-foreground">{title}</div>
        <div className="text-xs text-muted-foreground">{desc}</div>
      </div>
    </div>
  );
  return to ? <Link to={to}>{content}</Link> : content;
}
