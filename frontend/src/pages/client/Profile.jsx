import React, { useEffect, useState } from 'react';
import { Bell, Settings, DollarSign, CheckCircle, TrendingUp, Wallet, Briefcase } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';
import { useAuth } from '../../context/AuthContext';

export default function Profile() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [tab, setTab] = useState('overview');
  const [bookings, setBookings] = useState([]);

  useEffect(() => {
    const endpoint = user?.role === 'provider' ? '/stats/provider' : '/stats/customer';
    api.get(endpoint).then((r) => setStats(r.data)).catch(() => {});
    api.get('/bookings/mine').then((r) => setBookings(r.data)).catch(() => {});
  }, [user?.role]);

  const initials = (user?.name || 'U').split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase();
  const isProvider = user?.role === 'provider';

  const monthly = [
    { m: 'Feb', paid: 240, pending: 0 },
    { m: 'Mar', paid: 680, pending: 120 },
    { m: 'Apr', paid: 420, pending: 220 },
    { m: 'May', paid: 780, pending: 60 },
    { m: 'Jun', paid: 320, pending: 0 },
    { m: 'Jul', paid: 480, pending: 90 },
  ];
  const maxVal = Math.max(...monthly.map((m) => m.paid + m.pending));

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="rounded-2xl overflow-hidden bg-gradient-to-r from-primary via-blue-600 to-blue-700 text-white p-6 relative">
        <div className="flex items-center gap-4">
          {user?.picture ? (
            <img src={user.picture} alt={user.name} className="w-16 h-16 rounded-full object-cover ring-4 ring-white/20" />
          ) : (
            <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur ring-4 ring-white/20 text-xl font-bold flex items-center justify-center">{initials}</div>
          )}
          <div className="flex-1">
            <div className="text-2xl font-bold">{user?.name}</div>
            <div className="text-sm opacity-90">{user?.city} · Member since 2026</div>
            <Badge className="bg-white/20 hover:bg-white/30 text-white border-0 mt-1 capitalize">{user?.role}</Badge>
          </div>
          <div className="hidden sm:flex gap-2">
            <button className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"><Bell className="w-4 h-4" /></button>
            <button className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"><Settings className="w-4 h-4" /></button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
          {isProvider ? [
            { l: 'Earnings', v: stats ? `$${Math.round(stats.earnings)}` : '$0' },
            { l: 'Jobs Done', v: stats?.jobs_done || 0 },
            { l: 'Active', v: stats?.active_jobs || 0 },
            { l: 'Bids', v: stats?.pending_bids || 0 },
          ] : [
            { l: 'Upcoming', v: stats?.upcoming || 0 },
            { l: 'Active', v: stats?.active_jobs || 0 },
            { l: 'Completed', v: stats?.jobs_done || 0 },
            { l: 'Unpaid', v: stats?.unpaid || 0 },
          ].map((s) => (
            <div key={s.l} className="bg-white/10 backdrop-blur rounded-xl p-3">
              <div className="text-2xl font-bold">{s.v}</div>
              <div className="text-xs opacity-80">{s.l}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-6 border-b border-border">
        <div className="flex gap-1 -mb-px overflow-x-auto">
          {['overview', 'messages', 'invoices', 'jobs'].map((t) => (
            <button key={t} onClick={() => setTab(t)} className={`px-4 py-2 text-sm font-medium capitalize border-b-2 whitespace-nowrap transition-colors ${tab === t ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>{t}</button>
          ))}
        </div>
      </div>

      {tab === 'overview' && (
        <div className="mt-6 space-y-6">
          <div>
            <div className="text-sm font-semibold text-foreground mb-3">Service Dashboard</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <StatCard icon={DollarSign} label={isProvider ? 'Total Earnings' : 'Total Spent'} value={`$${stats?.[isProvider ? 'earnings' : 'total_spent'] || 0}`} sublabel={isProvider ? 'All time' : 'All invoices paid'} color="text-primary" />
              <StatCard icon={CheckCircle} label="Jobs Done" value={stats?.jobs_done || 0} sublabel="Completed" color="text-emerald-500" />
              <StatCard icon={TrendingUp} label="Active" value={stats?.active_jobs || 0} sublabel="In progress" color="text-amber-500" />
              <StatCard icon={Wallet} label={isProvider ? 'Rating' : 'Avg Cost'} value={isProvider ? '4.7★' : `$${Math.round(stats?.avg_cost || 0)}`} sublabel={isProvider ? '148 reviews' : 'Per completed job'} color="text-violet-500" />
            </div>
          </div>

          <div className="bg-card border border-border rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="font-semibold text-foreground">Monthly {isProvider ? 'Earnings' : 'Spending'}</div>
              <Badge variant="secondary" className="bg-rose-100 text-rose-600 dark:bg-rose-950/40 dark:text-rose-300">↑ 41% vs last month</Badge>
            </div>
            <div className="h-52 flex items-end gap-4">
              {monthly.map((m) => (
                <div key={m.m} className="flex-1 flex flex-col items-center gap-1">
                  <div className="w-full flex flex-col justify-end h-40">
                    {m.pending > 0 && <div style={{ height: `${(m.pending / maxVal) * 100}%` }} className="w-full bg-amber-400 rounded-t"></div>}
                    <div style={{ height: `${(m.paid / maxVal) * 100}%` }} className="w-full bg-primary rounded-t"></div>
                  </div>
                  <span className="text-xs text-muted-foreground">{m.m}</span>
                </div>
              ))}
            </div>
            <div className="flex items-center justify-center gap-4 mt-3 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-primary" /> Paid</span>
              <span className="inline-flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-amber-400" /> Pending</span>
            </div>
          </div>
        </div>
      )}

      {tab === 'jobs' && (
        <div className="mt-6 space-y-3">
          {bookings.length === 0 && <div className="text-muted-foreground text-center py-10">No jobs yet</div>}
          {bookings.slice(0, 20).map((b) => (
            <div key={b.booking_id} className="bg-card border border-border rounded-xl p-4 flex items-center justify-between">
              <div>
                <div className="font-medium text-foreground">{b.provider_name || b.client_name}</div>
                <div className="text-xs text-muted-foreground capitalize">{b.category} · {b.status}</div>
              </div>
              <div className="text-primary font-bold">${b.price}</div>
            </div>
          ))}
        </div>
      )}

      {tab === 'messages' && <div className="mt-6 text-center py-10 text-muted-foreground">Go to Messages tab in sidebar for full chat view.</div>}
      {tab === 'invoices' && (
        <div className="mt-6 bg-card border border-border rounded-2xl p-6">
          <div className="font-semibold text-foreground mb-3">Recent invoices</div>
          {bookings.filter((b) => b.status === 'paid' || b.status === 'done').slice(0, 10).map((b) => (
            <div key={b.booking_id} className="flex items-center justify-between py-2 border-b border-border last:border-b-0">
              <div>
                <div className="text-sm font-medium text-foreground">INV-{b.booking_id.slice(-6).toUpperCase()}</div>
                <div className="text-xs text-muted-foreground">{new Date(b.scheduled_at).toLocaleDateString()} · {b.provider_name}</div>
              </div>
              <div className="flex items-center gap-2">
                <Badge className={b.status === 'paid' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'}>{b.status}</Badge>
                <div className="font-bold">${b.price}</div>
              </div>
            </div>
          ))}
          {bookings.filter((b) => b.status === 'paid' || b.status === 'done').length === 0 && <div className="text-sm text-muted-foreground text-center py-6">No invoices yet</div>}
        </div>
      )}
    </div>
  );
}

function StatCard({ icon: Icon, label, value, sublabel, color }) {
  return (
    <div className="bg-card border border-border rounded-2xl p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs text-muted-foreground">{label}</div>
          <div className="text-2xl font-bold text-foreground mt-1">{value}</div>
          <div className="text-xs text-muted-foreground mt-0.5">{sublabel}</div>
        </div>
        <div className={`w-9 h-9 rounded-lg bg-muted/60 flex items-center justify-center ${color}`}><Icon className="w-4 h-4" /></div>
      </div>
    </div>
  );
}
