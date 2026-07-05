import React, { useEffect, useState } from 'react';
import { MessageSquare, Star, ShieldCheck, MapPin } from 'lucide-react';
import { Button } from '../../components/ui/button';
import api from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'sonner';

const statuses = ['booked', 'en_route', 'working', 'done', 'paid'];
const statusLabels = { booked: 'Booked', en_route: 'En Route', working: 'Working', done: 'Done', paid: 'Paid' };

export default function Bookings() {
  const [bookings, setBookings] = useState([]);
  const [filter, setFilter] = useState('all');
  const { user } = useAuth();

  const load = async () => {
    const r = await api.get('/bookings/mine');
    setBookings(r.data);
  };
  useEffect(() => { load(); }, []);

  const filtered = bookings.filter((b) => {
    if (filter === 'all') return true;
    if (filter === 'upcoming') return ['booked', 'en_route', 'working'].includes(b.status);
    if (filter === 'past') return ['done', 'paid', 'cancelled'].includes(b.status);
    return true;
  });

  const advance = async (booking) => {
    const idx = statuses.indexOf(booking.status);
    if (idx < 0 || idx === statuses.length - 1) return;
    const next = statuses[idx + 1];
    await api.patch(`/bookings/${booking.booking_id}/status`, { status: next });
    toast.success(`Marked as ${statusLabels[next]}`);
    load();
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">My Jobs</h1>
        <p className="text-sm text-muted-foreground">Job posts, bids & scheduled services</p>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
        {[{ k: 'all', l: 'All Bookings' }, { k: 'upcoming', l: 'Upcoming' }, { k: 'past', l: 'Past' }].map((f) => (
          <button key={f.k} onClick={() => setFilter(f.k)} className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${filter === f.k ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>{f.l}</button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="bg-card border border-border rounded-2xl p-12 text-center">
          <div className="text-lg font-medium text-foreground">No bookings yet</div>
          <p className="text-sm text-muted-foreground mt-1">Bookings appear here once a bid is accepted or a pro is dispatched.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((b) => {
            const currentIdx = statuses.indexOf(b.status);
            const isProvider = user.user_id === b.provider_id;
            return (
              <div key={b.booking_id} className="bg-card border border-border rounded-2xl overflow-hidden">
                <div className={`px-4 py-2 text-xs font-semibold ${b.status === 'done' || b.status === 'paid' ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300' : 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'} flex items-center justify-between`}>
                  <span>{statusLabels[b.status] || b.status}</span>
                  <span>{new Date(b.scheduled_at).toLocaleString()}</span>
                </div>
                <div className="p-4">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-blue-600 text-white text-sm font-bold flex items-center justify-center shrink-0">
                      {(isProvider ? b.client_name : b.provider_name).split(' ').map((s) => s[0]).slice(0, 2).join('')}
                    </div>
                    <div className="flex-1">
                      <div className="font-semibold text-foreground">{isProvider ? b.client_name : b.provider_name}</div>
                      <div className="text-sm text-muted-foreground capitalize">{b.category}</div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                        <Star className="w-3 h-3 fill-amber-400 text-amber-400" /> 4.7 · <ShieldCheck className="w-3 h-3 text-emerald-500" /> Verified
                      </div>
                    </div>
                    <div className="text-lg font-bold text-primary">${b.price}</div>
                  </div>

                  <div className="mt-4 relative">
                    <div className="absolute top-4 left-4 right-4 h-0.5 bg-muted"><div className="h-full bg-primary transition-all" style={{ width: `${(currentIdx / (statuses.length - 1)) * 100}%` }} /></div>
                    <div className="relative flex justify-between items-center">
                      {statuses.map((s, i) => (
                        <div key={s} className="flex flex-col items-center">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 border-card ${i <= currentIdx ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'} transition-colors`}>{i + 1}</div>
                          <span className="text-[10px] mt-1 text-muted-foreground">{statusLabels[s]}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 mt-4 text-xs text-muted-foreground">
                    <MapPin className="w-3 h-3" /> {b.address}
                  </div>

                  <div className="flex gap-2 mt-4">
                    <Button variant="outline" size="sm" className="flex-1"><MessageSquare className="w-3.5 h-3.5 mr-1" /> Message</Button>
                    {b.status !== 'paid' && b.status !== 'cancelled' && (
                      <Button size="sm" className="flex-1" onClick={() => advance(b)}>
                        Mark {statusLabels[statuses[currentIdx + 1]] || 'Next'}
                      </Button>
                    )}
                    {b.status === 'done' && <Button variant="secondary" size="sm" className="flex-1"><Star className="w-3.5 h-3.5 mr-1" /> Review</Button>}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
