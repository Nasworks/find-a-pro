import React, { useEffect, useState } from 'react';
import { History, CheckCircle, DollarSign, Star, Download } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';

export default function JobHistory() {
  const [bookings, setBookings] = useState([]);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    api.get('/job-history').then((r) => setBookings(r.data));
  }, []);

  const filtered = filter === 'all' ? bookings : bookings.filter((b) => b.status === filter);
  const totalRevenue = bookings.filter((b) => b.status === 'paid').reduce((s, b) => s + b.price, 0);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Job History</h1>
        <p className="text-sm text-muted-foreground">All completed & closed jobs</p>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-card border border-border rounded-2xl p-4">
          <div className="text-xs text-muted-foreground">Total jobs</div>
          <div className="text-2xl font-bold text-foreground mt-1">{bookings.length}</div>
        </div>
        <div className="bg-card border border-border rounded-2xl p-4">
          <div className="text-xs text-muted-foreground">Revenue</div>
          <div className="text-2xl font-bold text-emerald-600 mt-1">${totalRevenue.toFixed(0)}</div>
        </div>
        <div className="bg-card border border-border rounded-2xl p-4">
          <div className="text-xs text-muted-foreground">Avg rating</div>
          <div className="text-2xl font-bold text-foreground mt-1">4.8 <Star className="w-4 h-4 fill-amber-400 text-amber-400 inline" /></div>
        </div>
      </div>

      <div className="flex gap-2 mb-4 flex-wrap">
        {[
          { k: 'all', l: 'All' },
          { k: 'done', l: 'Completed' },
          { k: 'paid', l: 'Paid' },
          { k: 'cancelled', l: 'Cancelled' },
        ].map((f) => (
          <button key={f.k} onClick={() => setFilter(f.k)} className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${filter === f.k ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>{f.l}</button>
        ))}
        <Button size="sm" variant="outline" className="ml-auto"><Download className="w-3.5 h-3.5 mr-1" /> Export CSV</Button>
      </div>

      {filtered.length === 0 ? (
        <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
          <History className="w-10 h-10 mx-auto text-muted-foreground mb-3 opacity-40" />
          <div className="font-medium text-foreground">No history yet</div>
        </div>
      ) : (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-xs text-muted-foreground">
              <tr>
                <th className="text-left p-3">Job</th>
                <th className="text-left p-3">Client</th>
                <th className="text-left p-3">Date</th>
                <th className="text-left p-3">Status</th>
                <th className="text-right p-3">Amount</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((b) => (
                <tr key={b.booking_id} className="border-t border-border">
                  <td className="p-3 capitalize font-medium text-foreground">{b.category}</td>
                  <td className="p-3 text-muted-foreground">{b.client_name}</td>
                  <td className="p-3 text-muted-foreground">{new Date(b.scheduled_at).toLocaleDateString()}</td>
                  <td className="p-3"><Badge className={b.status === 'paid' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300' : b.status === 'done' ? 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300' : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'}>{b.status}</Badge></td>
                  <td className="p-3 text-right font-bold text-foreground">${b.price}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
