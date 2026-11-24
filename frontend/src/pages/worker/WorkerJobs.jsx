import React, { useCallback, useEffect, useState } from 'react';
import { MapPin, Play, Square, CheckCircle2, Loader2, Satellite, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';
import { getPosition, useGpsPings } from '../../hooks/useGps';
import { STATUS_STYLE, hrs } from '../../components/team/TeamAssignments';

const GPS_LABEL = { tracking: 'GPS on · auto timesheet active', waiting: 'Finding your location…', denied: 'Location blocked: allow it in your browser so auto timesheets work', unavailable: 'This device has no GPS' };

export default function WorkerJobs() {
  const [me, setMe] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    const [m, a] = await Promise.all([api.get('/worker/me'), api.get('/team/assignments')]);
    setMe(m.data);
    setJobs(a.data);
  }, []);
  useEffect(() => { load(); }, [load]);

  const gps = useGpsPings(!!me?.settings?.auto_timesheet_gps, (action) => {
    toast.success(action === 'started' ? 'Arrived on site: clocked in automatically' : 'Left the site: clocked out automatically');
    load();
  });

  const act = async (key, fn) => {
    setBusy(key);
    try { await fn(); await load(); } catch (e) { toast.error(e.response?.data?.detail || e.message); } finally { setBusy(null); }
  };
  const clockIn = (a) => act(a.assignment_id, async () => { await api.post('/worker/clock-in', { assignment_id: a.assignment_id, ...(await getPosition()) }); toast.success('Clocked in'); });
  const clockOut = () => act('out', async () => { await api.post('/worker/clock-out', await getPosition()); toast.success('Clocked out'); });
  const finish = (a) => act(`done-${a.assignment_id}`, async () => { await api.patch(`/team/assignments/${a.assignment_id}`, { status: 'done' }); toast.success('Job marked done'); });

  if (!me) return <div className="p-10 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;
  const open = jobs.filter((j) => j.status !== 'done');
  const done = jobs.filter((j) => j.status === 'done');

  return (
    <div className="p-4 sm:p-6 max-w-3xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-foreground">My jobs</h1>
        <p className="text-sm text-muted-foreground">{me.member.name} · {me.member.role} at {me.settings.company_name}</p>
      </div>

      <div className={`rounded-2xl p-4 flex items-center gap-3 ${me.running ? 'bg-blue-600 text-white' : 'bg-card border border-border'}`} data-testid="clock-status-card">
        <Clock className="w-5 h-5 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="font-semibold" data-testid="clock-status">{me.running ? `On the clock · ${me.running.job_title}` : 'Not clocked in'}</div>
          <div className={`text-xs ${me.running ? 'text-white/80' : 'text-muted-foreground'}`}>
            {me.running ? `Since ${new Date(me.running.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}${me.running.mode === 'geofence' ? ' (auto)' : ''}` : `This week: ${me.week_hours} h`}
          </div>
        </div>
        {me.running && <Button variant="secondary" onClick={clockOut} disabled={busy === 'out'} data-testid="clock-out-btn">{busy === 'out' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Square className="w-4 h-4 mr-1" />} Clock out</Button>}
      </div>

      {me.settings.auto_timesheet_gps && (
        <div className="text-xs inline-flex items-center gap-1.5 text-muted-foreground" data-testid="gps-status"><Satellite className="w-3.5 h-3.5 text-primary" /> {GPS_LABEL[gps] || 'GPS off'}</div>
      )}

      <section className="space-y-2" data-testid="worker-open-jobs">
        {open.length === 0 && <div className="bg-card border border-dashed border-border rounded-2xl p-10 text-center text-sm text-muted-foreground">No jobs right now. New jobs from your company show up here.</div>}
        {open.map((a) => <JobCard key={a.assignment_id} a={a} running={me.running} busy={busy} onIn={clockIn} onDone={finish} />)}
      </section>

      {done.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-muted-foreground mb-2">Finished</h2>
          {done.map((a) => <div key={a.assignment_id} className="flex justify-between text-sm py-2 border-b border-border" data-testid={`worker-done-${a.assignment_id}`}><span>{a.title}</span><span className="tabular-nums">{hrs(a.minutes_logged)}</span></div>)}
        </section>
      )}
    </div>
  );
}

function JobCard({ a, running, busy, onIn, onDone }) {
  const here = running?.assignment_id === a.assignment_id;
  return (
    <div className="bg-card border border-border rounded-2xl p-4" data-testid={`worker-job-${a.assignment_id}`}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-semibold text-foreground">{a.title}</span>
        <Badge className={STATUS_STYLE[a.status]}>{a.status.replace('_', ' ')}</Badge>
        <span className="ml-auto text-xs tabular-nums text-muted-foreground">{hrs(a.minutes_logged)} logged</span>
      </div>
      {a.scheduled_for && <div className="text-xs text-muted-foreground mt-1">{new Date(a.scheduled_for).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</div>}
      {a.address && <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(a.address)}`} target="_blank" rel="noreferrer" className="text-xs text-primary mt-1 inline-flex items-center gap-1"><MapPin className="w-3 h-3" /> {a.address}</a>}
      {a.description && <p className="text-sm text-muted-foreground mt-2">{a.description}</p>}
      {a.notes && <p className="text-sm mt-2 bg-amber-500/10 rounded-lg px-3 py-2">{a.notes}</p>}
      <div className="flex gap-2 mt-3">
        {!running && <Button size="sm" onClick={() => onIn(a)} disabled={busy === a.assignment_id} data-testid="clock-in-btn">{busy === a.assignment_id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 mr-1" />} Clock in</Button>}
        {!here && <Button size="sm" variant="outline" onClick={() => onDone(a)} disabled={busy === `done-${a.assignment_id}`} data-testid="mark-done-btn"><CheckCircle2 className="w-4 h-4 mr-1" /> Mark done</Button>}
      </div>
    </div>
  );
}
