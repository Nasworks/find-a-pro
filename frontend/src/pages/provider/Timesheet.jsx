import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Play, Square, Clock, DollarSign, MapPin, Fuel, ShoppingCart, Wrench, Car,
  Loader2, Plus, Trash2, Satellite, SatelliteDish, AlertCircle, CheckCircle2,
  Users as UsersIcon, ClipboardList,
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import api from '../../lib/api';
import { JobInvoice } from '../../components/JobInvoice';
import { toast } from 'sonner';

const TYPE_META = {
  work: { label: 'On job', icon: Wrench, color: 'bg-emerald-500', ring: 'ring-emerald-500/30', text: 'text-emerald-600' },
  travel: { label: 'Travel', icon: Car, color: 'bg-blue-500', ring: 'ring-blue-500/30', text: 'text-blue-600' },
  materials: { label: 'Materials', icon: ShoppingCart, color: 'bg-amber-500', ring: 'ring-amber-500/30', text: 'text-amber-600' },
};

const DEFAULT_GEOFENCE_RADIUS = 100; // metres
const GEOFENCE_EXIT_GRACE_MS = 60_000; // one-minute grace to avoid flickering

// ------- helpers -------
function haversineMetres(a, b) {
  if (!a || !b || a.lat == null || b.lat == null) return Infinity;
  const toRad = (d) => (d * Math.PI) / 180;
  const R = 6371000;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

function getPosition() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
      () => resolve(null),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 },
    );
  });
}

function fmtDuration(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

function fmtMinutes(mins) {
  const total = Math.round(mins);
  if (total < 60) return `${total} min`;
  const h = Math.floor(total / 60);
  const m = total % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

function groupByDate(entries) {
  const groups = {};
  for (const e of entries) {
    const d = (e.started_at || '').slice(0, 10);
    (groups[d] = groups[d] || []).push(e);
  }
  return Object.entries(groups).sort((a, b) => (a[0] < b[0] ? 1 : -1));
}

function fmtDay(key) {
  if (!key) return '';
  const d = new Date(key + 'T00:00:00');
  const today = new Date();
  const same = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  const yd = new Date(today); yd.setDate(today.getDate() - 1);
  if (same(d, today)) return 'Today';
  if (same(d, yd)) return 'Yesterday';
  return d.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'short' });
}

function fmtTime(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); } catch { return iso; }
}

// ------- page -------
export default function Timesheet() {
  const [active, setActive] = useState([]);
  const [entries, setEntries] = useState([]);
  const [summary, setSummary] = useState(null);
  const [team, setTeam] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0); // drives the running-clock refresh
  const [mode, setMode] = useState('manual'); // 'manual' | 'geofence'
  const [geofenceJobId, setGeofenceJobId] = useState('');
  const [geofenceRadius, setGeofenceRadius] = useState(DEFAULT_GEOFENCE_RADIUS);
  const [geofenceCoords, setGeofenceCoords] = useState(null);
  const [geofenceStatus, setGeofenceStatus] = useState('off'); // off | watching | inside | outside | error
  const [geofenceError, setGeofenceError] = useState('');
  const [addEntryOpen, setAddEntryOpen] = useState(false);

  const watchIdRef = useRef(null);
  const exitTimerRef = useRef(null);

  const refresh = async () => {
    try {
      const [a, e, s, t, j] = await Promise.all([
        api.get('/timesheets/active'),
        api.get('/timesheets/entries?limit=200'),
        api.get('/timesheets/summary'),
        api.get('/team'),
        api.get('/timesheets/jobs').catch(() => ({ data: [] })),
      ]);
      setActive(a.data);
      setEntries(e.data);
      setSummary(s.data);
      setTeam(t.data);
      setJobs(Array.isArray(j.data) ? j.data : (j.data?.jobs || []));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);
  // Running-clock tick — only when something is active.
  useEffect(() => {
    if (active.length === 0) return undefined;
    const id = setInterval(() => setTick((v) => v + 1), 1000);
    return () => clearInterval(id);
  }, [active.length]);

  const todayISO = new Date().toISOString().slice(0, 10);
  const todayMinutes = useMemo(() => entries
    .filter((e) => (e.started_at || '').startsWith(todayISO))
    .reduce((acc, e) => acc + (e.duration_minutes || 0), 0), [entries, todayISO]);
  const weekMinutes = useMemo(() => {
    const now = new Date();
    const weekStart = new Date(now);
    weekStart.setDate(now.getDate() - 7);
    return entries
      .filter((e) => new Date(e.started_at) >= weekStart)
      .reduce((acc, e) => acc + (e.duration_minutes || 0), 0);
  }, [entries]);

  // ------- timer ops -------
  const startTimer = async (opts) => {
    try {
      const { type = 'work', worker_id, job_id, mode: m = 'manual', notes } = opts;
      const pos = geofenceCoords || await getPosition();
      const lat = pos?.lat;
      const lng = pos?.lng;
      const res = await api.post('/timesheets/start', { type, worker_id: worker_id || undefined, job_id: job_id || undefined, mode: m, notes, lat, lng });
      if (!res.data.ok && res.data.error === 'already_running') {
        toast.info('A timer is already running for this worker');
      } else {
        toast.success(`${TYPE_META[type]?.label || 'Timer'} started`);
      }
      refresh();
      return res.data.entry;
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not start timer');
      return null;
    }
  };

  const stopTimer = async (entryId) => {
    try {
      const pos = geofenceCoords || await getPosition();
      const lat = pos?.lat;
      const lng = pos?.lng;
      const res = await api.post(`/timesheets/stop/${entryId}`, { lat, lng });
      toast.success(`Stopped — ${fmtMinutes(res.data.entry.duration_minutes)} · $${res.data.entry.cost}`);
      refresh();
    } catch {
      toast.error('Could not stop timer');
    }
  };

  const removeEntry = async (entryId) => {
    if (!window.confirm('Delete this time entry?')) return;
    await api.delete(`/timesheets/entries/${entryId}`);
    toast.success('Entry removed');
    refresh();
  };

  // ------- geofence -------
  const selectedGeofenceJob = useMemo(() => jobs.find((j) => j.job_id === geofenceJobId), [jobs, geofenceJobId]);

  const stopGeofence = () => {
    if (watchIdRef.current != null && navigator.geolocation) {
      try { navigator.geolocation.clearWatch(watchIdRef.current); } catch (_) { /* noop */ }
    }
    watchIdRef.current = null;
    if (exitTimerRef.current) clearTimeout(exitTimerRef.current);
    exitTimerRef.current = null;
    setGeofenceStatus('off');
  };

  const onGeofencePosition = (pos) => {
    const here = { lat: pos.coords.latitude, lng: pos.coords.longitude };
    setGeofenceCoords(here);
    setGeofenceError('');
    const job = selectedGeofenceJob;
    if (!job || job.latitude == null || job.longitude == null) {
      setGeofenceStatus('watching');
      return;
    }
    const dist = haversineMetres(here, { lat: job.latitude, lng: job.longitude });
    const inside = dist <= geofenceRadius;
    setGeofenceStatus(inside ? 'inside' : 'outside');
    // Find active entry for the geofence job (if any) belonging to self.
    const selfActive = active.find((e) => e.worker_id === e.provider_id && e.job_id === job.job_id && e.mode === 'geofence');
    if (inside && !selfActive) {
      startTimer({ type: 'work', job_id: job.job_id, mode: 'geofence', notes: 'Auto-started by geofence' });
    } else if (!inside && selfActive) {
      // One-minute grace window to avoid flapping.
      if (exitTimerRef.current) clearTimeout(exitTimerRef.current);
      exitTimerRef.current = setTimeout(() => stopTimer(selfActive.entry_id), GEOFENCE_EXIT_GRACE_MS);
    } else if (inside && selfActive && exitTimerRef.current) {
      clearTimeout(exitTimerRef.current);
      exitTimerRef.current = null;
    }
  };

  const onGeofenceError = (err) => {
    setGeofenceError(err?.message || 'Could not read GPS');
    setGeofenceStatus('error');
  };

  const startGeofence = () => {
    if (!navigator.geolocation) {
      toast.error('Your browser does not expose GPS');
      return;
    }
    if (!geofenceJobId) {
      toast.error('Pick a job first');
      return;
    }
    stopGeofence();
    setGeofenceStatus('watching');
    watchIdRef.current = navigator.geolocation.watchPosition(onGeofencePosition, onGeofenceError, {
      enableHighAccuracy: true, maximumAge: 10000, timeout: 20000,
    });
  };

  // Cleanup geolocation on unmount.
  useEffect(() => () => stopGeofence(), []);

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-6" data-testid="timesheet-page">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-blue-600 text-white flex items-center justify-center shadow-lg shadow-primary/20">
          <Clock className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-2xl md:text-3xl font-bold">Timesheet</h1>
          <p className="text-sm text-muted-foreground">Track labour, travel and materials — to the minute.</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" data-testid="add-entry-btn" onClick={() => setAddEntryOpen(true)}>
            <Plus className="w-4 h-4 mr-1" /> Add entry
          </Button>
        </div>
      </div>

      {/* Active timers strip */}
      <ActiveTimers active={active} onStop={stopTimer} tick={tick} />

      {/* Totals */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <StatTile label="Today" value={fmtMinutes(todayMinutes)} sub={summary ? `$${entries.filter((e) => (e.started_at || '').startsWith(todayISO)).reduce((a, e) => a + (e.cost || 0), 0).toFixed(2)}` : null} icon={Clock} />
        <StatTile label="Last 7 days" value={fmtMinutes(weekMinutes)} icon={ClipboardList} />
        <StatTile label="Billable" value={summary ? `$${summary.billable_cost.toFixed(2)}` : '—'} icon={DollarSign} />
        <StatTile label="Fuel" value={summary ? `$${summary.fuel_cost.toFixed(2)}` : '—'} icon={Fuel} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: quick start + geofence */}
        <div className="space-y-4">
          <QuickStartPanel mode={mode} setMode={setMode} team={team} jobs={jobs} startTimer={startTimer} active={active} />
          {mode === 'geofence' && (
            <GeofencePanel
              status={geofenceStatus}
              coords={geofenceCoords}
              job={selectedGeofenceJob}
              jobs={jobs}
              geofenceJobId={geofenceJobId}
              setGeofenceJobId={setGeofenceJobId}
              radius={geofenceRadius}
              setRadius={setGeofenceRadius}
              start={startGeofence}
              stop={stopGeofence}
              error={geofenceError}
            />
          )}
          <InvoicePanel jobs={jobs} refreshKey={`${entries.length}-${summary?.total_cost}`} />
        </div>

        {/* Right: entries list */}
        <div className="lg:col-span-2">
          <EntriesList
            loading={loading}
            entries={entries}
            onRemove={removeEntry}
          />
        </div>
      </div>

      <AddEntryDialog
        open={addEntryOpen}
        onOpenChange={setAddEntryOpen}
        team={team}
        jobs={jobs}
        onSaved={refresh}
      />
    </div>
  );
}

// ------- active timers strip -------
function ActiveTimers({ active, onStop, tick }) { // eslint-disable-line no-unused-vars
  if (active.length === 0) return (
    <div className="mb-4 p-4 rounded-2xl border border-dashed border-border bg-card text-center text-sm text-muted-foreground" data-testid="no-active-timers">
      No active timers — start one below.
    </div>
  );
  return (
    <div className="mb-4 space-y-2" data-testid="active-timers">
      {active.map((e) => {
        const meta = TYPE_META[e.type] || TYPE_META.work;
        const Icon = meta.icon;
        const elapsed = (e.duration_seconds || 0) + Math.floor((Date.now() - (new Date(e.started_at).getTime())) / 1000) - (e.duration_seconds || 0);
        const seconds = Math.max(0, Math.floor((Date.now() - new Date(e.started_at).getTime()) / 1000));
        void elapsed;
        const minutes = seconds / 60;
        const liveCost = (minutes * ((e.hourly_rate_snapshot || 0) / 60)).toFixed(2);
        return (
          <div
            key={e.entry_id}
            data-testid={`active-timer-${e.entry_id}`}
            className={`flex items-center gap-3 p-4 rounded-2xl bg-card border border-border ring-2 ${meta.ring} shadow-md`}
          >
            <div className={`w-10 h-10 rounded-xl ${meta.color} text-white flex items-center justify-center shrink-0`}>
              <Icon className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge className={`${meta.color} text-white border-transparent`}>{meta.label}</Badge>
                <Badge variant="outline" className="text-[10px]">{e.mode === 'geofence' ? 'GPS auto' : 'Manual'}</Badge>
                <span className="text-sm font-medium truncate">{e.worker_name}</span>
                {e.job_title && <span className="text-xs text-muted-foreground truncate">· {e.job_title}</span>}
              </div>
              <div className="text-xs text-muted-foreground">Started {fmtTime(e.started_at)}{e.notes ? ` · ${e.notes}` : ''}</div>
            </div>
            <div className="text-right">
              <div className="text-xl font-bold tabular-nums">{fmtDuration(seconds)}</div>
              <div className="text-xs text-muted-foreground">${liveCost} @ ${e.hourly_rate_snapshot}/h</div>
            </div>
            <Button
              data-testid={`stop-timer-${e.entry_id}`}
              variant="destructive"
              size="sm"
              onClick={() => onStop(e.entry_id)}
            >
              <Square className="w-4 h-4 mr-1" /> Stop
            </Button>
          </div>
        );
      })}
    </div>
  );
}

function StatTile({ label, value, sub, icon: Icon }) {
  return (
    <div className="bg-card border border-border rounded-2xl p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs text-muted-foreground">{label}</div>
          <div className="text-2xl font-bold tabular-nums">{value}</div>
          {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
        </div>
        <Icon className="w-4 h-4 text-muted-foreground" />
      </div>
    </div>
  );
}

// ------- quick-start -------
function QuickStartPanel({ mode, setMode, team, jobs, startTimer, active }) {
  const [worker, setWorker] = useState('self');
  const [job, setJob] = useState('none');
  const [notes, setNotes] = useState('');
  const workerId = worker === 'self' ? undefined : worker;
  const jobId = job === 'none' ? undefined : job;
  const anyActive = active.some((e) => (e.worker_id === workerId) || (!workerId && e.worker_id === e.provider_id));

  const kick = (type) => {
    startTimer({ type, worker_id: workerId, job_id: jobId, mode: 'manual', notes: notes || undefined });
    setNotes('');
  };

  return (
    <div className="bg-card border border-border rounded-2xl p-4" data-testid="quick-start-panel">
      <div className="flex items-center gap-2 mb-3">
        <h2 className="font-semibold">Start a timer</h2>
        <div className="ml-auto inline-flex rounded-lg border border-border p-0.5">
          <button
            data-testid="mode-manual"
            onClick={() => setMode('manual')}
            className={`text-xs px-2 py-1 rounded-md ${mode === 'manual' ? 'bg-accent text-foreground' : 'text-muted-foreground'}`}
          >Manual</button>
          <button
            data-testid="mode-geofence"
            onClick={() => setMode('geofence')}
            className={`text-xs px-2 py-1 rounded-md inline-flex items-center gap-1 ${mode === 'geofence' ? 'bg-accent text-foreground' : 'text-muted-foreground'}`}
          ><Satellite className="w-3 h-3" />GPS</button>
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <Label className="text-xs">Worker</Label>
          <Select value={worker} onValueChange={setWorker}>
            <SelectTrigger data-testid="worker-select" className="mt-1"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="self">You</SelectItem>
              {team.map((m) => <SelectItem key={m.member_id} value={m.member_id}>{m.name} · ${m.hourly_rate}/h</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs">Job</Label>
          <Select value={job} onValueChange={setJob}>
            <SelectTrigger data-testid="job-select" className="mt-1"><SelectValue placeholder="Optional" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">— No job —</SelectItem>
              {jobs.map((j) => <SelectItem key={j.job_id} value={j.job_id}>{j.title}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs">Notes (optional)</Label>
          <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. Replacing hot water cylinder" className="mt-1" data-testid="notes-input" />
        </div>
        <div className="grid grid-cols-3 gap-2 pt-1">
          <Button data-testid="start-work" disabled={anyActive} onClick={() => kick('work')} className="bg-emerald-500 hover:bg-emerald-600"><Wrench className="w-4 h-4 mr-1" />Work</Button>
          <Button data-testid="start-travel" disabled={anyActive} onClick={() => kick('travel')} className="bg-blue-500 hover:bg-blue-600"><Car className="w-4 h-4 mr-1" />Travel</Button>
          <Button data-testid="start-materials" disabled={anyActive} onClick={() => kick('materials')} className="bg-amber-500 hover:bg-amber-600"><ShoppingCart className="w-4 h-4 mr-1" />Mats</Button>
        </div>
        {anyActive && <p className="text-xs text-amber-600 inline-flex items-center gap-1"><AlertCircle className="w-3 h-3" />A timer is already running for this worker — stop it to start a new one.</p>}
      </div>
    </div>
  );
}

// ------- geofence -------
function GeofencePanel({ status, coords, job, jobs, geofenceJobId, setGeofenceJobId, radius, setRadius, start, stop, error }) {
  const distance = useMemo(() => {
    if (!coords || !job || job.latitude == null) return null;
    return haversineMetres(coords, { lat: job.latitude, lng: job.longitude });
  }, [coords, job]);

  const statusMeta = {
    off: { label: 'GPS off', color: 'bg-gray-200 text-gray-700 dark:bg-gray-800 dark:text-gray-300' },
    watching: { label: 'Locating…', color: 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300' },
    inside: { label: 'Inside geofence — timer running', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300' },
    outside: { label: 'Outside geofence', color: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300' },
    error: { label: 'GPS error', color: 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300' },
  }[status] || { label: status, color: 'bg-muted text-foreground' };

  return (
    <div className="bg-card border border-primary/30 rounded-2xl p-4 shadow-md shadow-primary/5" data-testid="geofence-panel">
      <div className="flex items-center gap-2 mb-2">
        <SatelliteDish className="w-4 h-4 text-primary" />
        <h2 className="font-semibold">Geofence auto-timer</h2>
        <Badge className={`ml-auto ${statusMeta.color}`} data-testid="geofence-status">{statusMeta.label}</Badge>
      </div>
      <p className="text-xs text-muted-foreground mb-3">Keep this tab open — we&apos;ll auto-start when you arrive and auto-stop one minute after you leave.</p>
      <div className="space-y-3">
        <div>
          <Label className="text-xs">Job to track</Label>
          <Select value={geofenceJobId || 'none'} onValueChange={(v) => setGeofenceJobId(v === 'none' ? '' : v)}>
            <SelectTrigger data-testid="geofence-job-select" className="mt-1"><SelectValue placeholder="Pick a job" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">— Pick a job —</SelectItem>
              {jobs.filter((j) => j.latitude != null && j.longitude != null).map((j) => (
                <SelectItem key={j.job_id} value={j.job_id}>{j.title}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          {job && job.latitude == null && <p className="text-xs text-amber-600 mt-1">This job has no GPS coordinates.</p>}
        </div>
        <div>
          <Label className="text-xs">Radius: {radius} m</Label>
          <Input
            type="range" min={30} max={500} step={10}
            value={radius}
            onChange={(e) => setRadius(Number(e.target.value))}
            data-testid="geofence-radius"
            className="mt-1"
          />
        </div>
        {distance != null && (
          <div className="text-xs text-muted-foreground inline-flex items-center gap-1">
            <MapPin className="w-3 h-3" /> You&apos;re <strong className="text-foreground">{Math.round(distance)} m</strong> from the site
          </div>
        )}
        {error && <p className="text-xs text-rose-500">{error}</p>}
        <div className="flex gap-2">
          {status === 'off' || status === 'error' ? (
            <Button data-testid="start-geofence" onClick={start} className="flex-1"><Satellite className="w-4 h-4 mr-1" />Enable GPS</Button>
          ) : (
            <Button data-testid="stop-geofence" variant="outline" onClick={stop} className="flex-1">Stop GPS</Button>
          )}
        </div>
      </div>
    </div>
  );
}

// ------- entries list -------
function EntriesList({ loading, entries: all, onRemove }) {
  const entries = all.filter((e) => !e.is_running);
  if (loading) return <div className="py-16 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;
  if (entries.length === 0) return (
    <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
      <Clock className="w-8 h-8 mx-auto text-muted-foreground opacity-40 mb-2" />
      <div className="font-medium">No entries yet</div>
      <p className="text-sm text-muted-foreground mt-1">Start your first timer or add a completed entry.</p>
    </div>
  );
  return (
    <div className="space-y-5" data-testid="entries-list">
      {groupByDate(entries).map(([day, items]) => (
        <div key={day}>
          <div className="flex items-baseline justify-between mb-2">
            <div className="text-sm font-semibold text-muted-foreground">{fmtDay(day)}</div>
            <div className="text-xs text-muted-foreground">
              {fmtMinutes(items.reduce((a, e) => a + (e.duration_minutes || 0), 0))} · $
              {items.reduce((a, e) => a + (e.cost || 0), 0).toFixed(2)}
            </div>
          </div>
          <div className="space-y-2">
            {items.map((e) => <EntryRow key={e.entry_id} e={e} onRemove={onRemove} />)}
          </div>
        </div>
      ))}
    </div>
  );
}

function EntryRow({ e, onRemove }) {
  const meta = TYPE_META[e.type] || TYPE_META.work;
  const Icon = meta.icon;
  return (
    <div className="bg-card border border-border rounded-xl p-3 flex items-center gap-3 group hover:border-primary/40 transition-colors" data-testid={`entry-row-${e.entry_id}`}>
      <div className={`w-9 h-9 rounded-lg ${meta.color} text-white flex items-center justify-center shrink-0`}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium truncate">{e.job_title || (e.type === 'travel' ? 'Travel' : e.type === 'materials' ? 'Materials run' : 'Ad-hoc work')}</span>
          {e.worker_name && <span className="text-xs text-muted-foreground">· {e.worker_name}</span>}
          {e.mode === 'geofence' && <Badge variant="outline" className="text-[10px]"><Satellite className="w-2.5 h-2.5 mr-0.5" />GPS</Badge>}
          {!e.billable && <Badge variant="outline" className="text-[10px]">non-billable</Badge>}
        </div>
        <div className="text-xs text-muted-foreground truncate">
          {fmtTime(e.started_at)} – {fmtTime(e.ended_at)}
          {e.fuel_cost != null && <> · <Fuel className="inline w-3 h-3" /> ${e.fuel_cost}{e.fuel_km != null ? ` · ${e.fuel_km} km` : ''}</>}
          {e.notes && <> · {e.notes}</>}
        </div>
        <EntryLocation e={e} />
      </div>
      <div className="text-right shrink-0">
        <div className="font-semibold tabular-nums">{fmtMinutes(e.duration_minutes || 0)}</div>
        <div className="text-xs text-muted-foreground">${(e.cost || 0).toFixed(2)}</div>
      </div>
      <button
        onClick={() => onRemove(e.entry_id)}
        className="text-muted-foreground hover:text-rose-500 transition-colors"
        data-testid={`remove-entry-${e.entry_id}`}
        aria-label="Delete entry"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  );
}

// ------- add entry dialog (retro + travel + materials with fuel) -------
function AddEntryDialog({ open, onOpenChange, team, jobs, onSaved }) {
  const empty = { type: 'work', worker_id: 'self', job_id: 'none', started_date: '', started_time: '', ended_date: '', ended_time: '', fuel_km: '', fuel_cost: '', notes: '', billable: true };
  const [form, setForm] = useState(empty);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    const now = new Date();
    const d = now.toISOString().slice(0, 10);
    const t = now.toTimeString().slice(0, 5);
    setForm({ ...empty, started_date: d, started_time: t, ended_date: d, ended_time: t });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const save = async () => {
    if (!form.started_date || !form.started_time || !form.ended_date || !form.ended_time) {
      toast.error('Enter start and end times');
      return;
    }
    const started_at = new Date(`${form.started_date}T${form.started_time}`).toISOString();
    const ended_at = new Date(`${form.ended_date}T${form.ended_time}`).toISOString();
    if (new Date(started_at) >= new Date(ended_at)) {
      toast.error('End must be after start');
      return;
    }
    setBusy(true);
    try {
      await api.post('/timesheets/entries', {
        type: form.type,
        worker_id: form.worker_id === 'self' ? undefined : form.worker_id,
        job_id: form.job_id === 'none' ? undefined : form.job_id,
        started_at, ended_at,
        fuel_km: form.fuel_km || undefined,
        fuel_cost: form.fuel_cost || undefined,
        notes: form.notes || undefined,
        billable: form.billable,
      });
      toast.success('Entry added');
      onOpenChange(false);
      onSaved?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not add entry');
    } finally {
      setBusy(false);
    }
  };

  const showFuel = form.type === 'travel' || form.type === 'materials';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="add-entry-dialog">
        <DialogHeader><DialogTitle>Add time entry</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(TYPE_META).map(([k, meta]) => {
              const I = meta.icon;
              const selected = form.type === k;
              return (
                <button
                  key={k}
                  data-testid={`add-type-${k}`}
                  onClick={() => setForm((f) => ({ ...f, type: k }))}
                  className={`p-3 rounded-xl border transition-all inline-flex flex-col items-center gap-1 ${selected ? 'border-primary bg-primary/10' : 'border-border hover:border-primary/40'}`}
                >
                  <I className={`w-4 h-4 ${meta.text}`} />
                  <span className="text-xs font-medium">{meta.label}</span>
                </button>
              );
            })}
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label className="text-xs">Worker</Label>
              <Select value={form.worker_id} onValueChange={(v) => setForm((f) => ({ ...f, worker_id: v }))}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="self">You</SelectItem>
                  {team.map((m) => <SelectItem key={m.member_id} value={m.member_id}>{m.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Job</Label>
              <Select value={form.job_id} onValueChange={(v) => setForm((f) => ({ ...f, job_id: v }))}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">— No job —</SelectItem>
                  {jobs.map((j) => <SelectItem key={j.job_id} value={j.job_id}>{j.title}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label className="text-xs">Start date</Label>
              <Input type="date" value={form.started_date} onChange={(e) => setForm((f) => ({ ...f, started_date: e.target.value }))} className="mt-1" />
            </div>
            <div>
              <Label className="text-xs">Start time</Label>
              <Input type="time" value={form.started_time} onChange={(e) => setForm((f) => ({ ...f, started_time: e.target.value }))} className="mt-1" />
            </div>
            <div>
              <Label className="text-xs">End date</Label>
              <Input type="date" value={form.ended_date} onChange={(e) => setForm((f) => ({ ...f, ended_date: e.target.value }))} className="mt-1" />
            </div>
            <div>
              <Label className="text-xs">End time</Label>
              <Input type="time" value={form.ended_time} onChange={(e) => setForm((f) => ({ ...f, ended_time: e.target.value }))} className="mt-1" />
            </div>
          </div>

          {showFuel && (
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs">Kilometres</Label>
                <Input type="number" min="0" step="0.1" value={form.fuel_km} onChange={(e) => setForm((f) => ({ ...f, fuel_km: e.target.value }))} className="mt-1" placeholder="e.g. 12" />
              </div>
              <div>
                <Label className="text-xs">Fuel cost ($)</Label>
                <Input type="number" min="0" step="0.01" value={form.fuel_cost} onChange={(e) => setForm((f) => ({ ...f, fuel_cost: e.target.value }))} className="mt-1" placeholder="e.g. 8.50" />
              </div>
            </div>
          )}

          <div>
            <Label className="text-xs">Notes</Label>
            <Input value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} className="mt-1" placeholder="Optional" />
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.billable} onChange={(e) => setForm((f) => ({ ...f, billable: e.target.checked }))} />
            Billable to customer (included in invoice total)
          </label>

          <Button onClick={save} disabled={busy} className="w-full" data-testid="save-entry">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <><CheckCircle2 className="w-4 h-4 mr-1" />Save entry</>}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

const locLink = (lat, lng) => `https://www.google.com/maps?q=${lat},${lng}`;

function EntryLocation({ e }) {
  const hasStart = e.started_lat != null && e.started_lng != null;
  const hasEnd = e.ended_lat != null && e.ended_lng != null;
  if (!hasStart && !hasEnd) return null;
  return (
    <div className="text-[11px] text-muted-foreground flex items-center gap-2 mt-0.5" data-testid={`entry-location-${e.entry_id}`}>
      <MapPin className="w-3 h-3 text-primary" />
      {hasStart && <a href={locLink(e.started_lat, e.started_lng)} target="_blank" rel="noreferrer" className="hover:text-primary hover:underline">Start {Number(e.started_lat).toFixed(4)}, {Number(e.started_lng).toFixed(4)}</a>}
      {hasEnd && <a href={locLink(e.ended_lat, e.ended_lng)} target="_blank" rel="noreferrer" className="hover:text-primary hover:underline">Stop {Number(e.ended_lat).toFixed(4)}, {Number(e.ended_lng).toFixed(4)}</a>}
    </div>
  );
}

function InvoicePanel({ jobs, refreshKey }) {
  const [jobId, setJobId] = useState('');
  const current = jobId || jobs[0]?.job_id || '';
  if (jobs.length === 0) return null;
  return (
    <div className="space-y-2" data-testid="invoice-panel">
      <Label className="text-xs">Invoice preview for job</Label>
      <Select value={current} onValueChange={setJobId}>
        <SelectTrigger data-testid="invoice-job-select"><SelectValue /></SelectTrigger>
        <SelectContent>
          {jobs.map((j) => <SelectItem key={j.job_id} value={j.job_id}>{j.title}</SelectItem>)}
        </SelectContent>
      </Select>
      <JobInvoice key={`${current}-${refreshKey}`} jobId={current} />
    </div>
  );
}
