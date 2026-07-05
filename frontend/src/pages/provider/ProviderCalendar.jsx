import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Clock } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';

export default function ProviderCalendar() {
  const [bookings, setBookings] = useState([]);
  const [current, setCurrent] = useState(new Date());

  useEffect(() => {
    api.get('/bookings/mine').then((r) => setBookings(r.data));
  }, []);

  const startOfMonth = new Date(current.getFullYear(), current.getMonth(), 1);
  const endOfMonth = new Date(current.getFullYear(), current.getMonth() + 1, 0);
  const startDay = startOfMonth.getDay();
  const daysInMonth = endOfMonth.getDate();
  const cells = [];
  for (let i = 0; i < startDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const bookingsByDay = {};
  bookings.forEach((b) => {
    const d = new Date(b.scheduled_at);
    if (d.getMonth() === current.getMonth() && d.getFullYear() === current.getFullYear()) {
      const day = d.getDate();
      if (!bookingsByDay[day]) bookingsByDay[day] = [];
      bookingsByDay[day].push(b);
    }
  });

  const monthLabel = current.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const today = new Date();

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Calendar</h1>
          <p className="text-sm text-muted-foreground">Your bookings & schedule</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => setCurrent(new Date(current.getFullYear(), current.getMonth() - 1))}><ChevronLeft className="w-4 h-4" /></Button>
          <div className="font-medium text-foreground min-w-[160px] text-center">{monthLabel}</div>
          <Button variant="outline" size="icon" onClick={() => setCurrent(new Date(current.getFullYear(), current.getMonth() + 1))}><ChevronRight className="w-4 h-4" /></Button>
        </div>
      </div>

      <div className="bg-card border border-border rounded-2xl p-4">
        <div className="grid grid-cols-7 gap-1 mb-2">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
            <div key={d} className="text-xs font-semibold text-muted-foreground text-center py-2">{d}</div>
          ))}
        </div>
        <div className="grid grid-cols-7 gap-1">
          {cells.map((d, i) => {
            const isToday = d === today.getDate() && current.getMonth() === today.getMonth() && current.getFullYear() === today.getFullYear();
            const dayBookings = d ? bookingsByDay[d] || [] : [];
            return (
              <div key={i} className={`min-h-[80px] p-1.5 rounded-lg border ${d ? 'border-border' : 'border-transparent'} ${isToday ? 'bg-primary/5 border-primary/40' : ''}`}>
                {d && (
                  <>
                    <div className={`text-xs font-medium ${isToday ? 'text-primary' : 'text-foreground'}`}>{d}</div>
                    <div className="mt-1 space-y-0.5">
                      {dayBookings.slice(0, 2).map((b) => (
                        <div key={b.booking_id} className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary truncate">{b.client_name || b.category}</div>
                      ))}
                      {dayBookings.length > 2 && <div className="text-[10px] text-muted-foreground">+{dayBookings.length - 2} more</div>}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-6">
        <div className="font-semibold text-foreground mb-3">Upcoming</div>
        <div className="space-y-2">
          {bookings.filter((b) => new Date(b.scheduled_at) >= today && b.status !== 'cancelled').slice(0, 5).map((b) => (
            <div key={b.booking_id} className="bg-card border border-border rounded-xl p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center"><Clock className="w-4 h-4" /></div>
                <div>
                  <div className="font-medium text-foreground">{b.client_name}</div>
                  <div className="text-xs text-muted-foreground capitalize">{b.category} · {new Date(b.scheduled_at).toLocaleString()}</div>
                </div>
              </div>
              <Badge className="capitalize">{b.status}</Badge>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
