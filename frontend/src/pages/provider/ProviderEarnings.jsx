import React, { useEffect, useState } from 'react';
import { DollarSign, TrendingUp, Download, CheckCircle } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';

export default function ProviderEarnings() {
  const [bookings, setBookings] = useState([]);
  const [stats, setStats] = useState({});

  useEffect(() => {
    api.get('/bookings/mine').then((r) => setBookings(r.data));
    api.get('/stats/provider').then((r) => setStats(r.data)).catch(() => {});
  }, []);

  const paid = bookings.filter((b) => b.status === 'paid');
  const pending = bookings.filter((b) => b.status === 'done');
  const totalPaid = paid.reduce((s, b) => s + b.price, 0);
  const totalPending = pending.reduce((s, b) => s + b.price, 0);

  const monthly = [
    { m: 'Feb', v: 1240 }, { m: 'Mar', v: 2680 }, { m: 'Apr', v: 1820 },
    { m: 'May', v: 3480 }, { m: 'Jun', v: 2120 }, { m: 'Jul', v: 2980 },
  ];
  const max = Math.max(...monthly.map((m) => m.v));

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Earnings</h1>
        <p className="text-sm text-muted-foreground">Track your income & payouts</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-primary to-blue-600 text-white rounded-2xl p-5">
          <div className="text-xs opacity-90">Total Earnings</div>
          <div className="text-3xl font-bold mt-2">${totalPaid.toFixed(0)}</div>
          <div className="text-xs opacity-90 mt-1">All time · {paid.length} jobs</div>
        </div>
        <div className="bg-card border border-border rounded-2xl p-5">
          <div className="text-xs text-muted-foreground">Pending Payout</div>
          <div className="text-3xl font-bold text-foreground mt-2">${totalPending.toFixed(0)}</div>
          <div className="text-xs text-muted-foreground mt-1">{pending.length} jobs awaiting payment</div>
        </div>
        <div className="bg-card border border-border rounded-2xl p-5">
          <div className="text-xs text-muted-foreground">This Month</div>
          <div className="text-3xl font-bold text-foreground mt-2">$2,980</div>
          <div className="text-xs text-emerald-600 mt-1 inline-flex items-center gap-1"><TrendingUp className="w-3 h-3" /> +18% vs last month</div>
        </div>
      </div>

      <div className="bg-card border border-border rounded-2xl p-5">
        <div className="font-semibold text-foreground mb-4">Monthly Earnings</div>
        <div className="h-48 flex items-end gap-4">
          {monthly.map((m) => (
            <div key={m.m} className="flex-1 flex flex-col items-center gap-1">
              <div className="text-[10px] text-muted-foreground">${m.v}</div>
              <div className="w-full bg-primary rounded-t" style={{ height: `${(m.v / max) * 100}%` }} />
              <span className="text-xs text-muted-foreground">{m.m}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-card border border-border rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="font-semibold text-foreground">Recent Payouts</div>
          <Button variant="outline" size="sm"><Download className="w-3.5 h-3.5 mr-1.5" /> Export</Button>
        </div>
        {bookings.filter((b) => b.status === 'paid' || b.status === 'done').slice(0, 10).map((b) => (
          <div key={b.booking_id} className="flex items-center justify-between py-3 border-b border-border last:border-b-0">
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${b.status === 'paid' ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-300' : 'bg-amber-100 text-amber-600 dark:bg-amber-950/60 dark:text-amber-300'}`}>
                {b.status === 'paid' ? <CheckCircle className="w-4 h-4" /> : <DollarSign className="w-4 h-4" />}
              </div>
              <div>
                <div className="text-sm font-medium text-foreground">{b.client_name}</div>
                <div className="text-xs text-muted-foreground capitalize">{b.category} · {new Date(b.scheduled_at).toLocaleDateString()}</div>
              </div>
            </div>
            <div className="text-right">
              <div className="font-bold text-foreground">${b.price}</div>
              <Badge className={b.status === 'paid' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'}>{b.status}</Badge>
            </div>
          </div>
        ))}
        {bookings.filter((b) => b.status === 'paid' || b.status === 'done').length === 0 && <div className="text-sm text-muted-foreground text-center py-8">No payouts yet</div>}
      </div>
    </div>
  );
}
