import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Zap, MapPin, CalendarDays, Tag, Clock, ClipboardList, Loader2, CheckCircle2, Play, Hourglass, Home as HomeIcon, Building2, X } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import api from '../lib/api';
import { toast } from 'sonner';

export const SIZE_META = {
  small_fixed: { l: 'Small fixed price', icon: Tag, cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' },
  hourly: { l: 'Hourly', icon: Clock, cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
  large_quote: { l: 'Project quote', icon: ClipboardList, cls: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300' },
};

export const priceLine = (j) => {
  if (j.pricing_type === 'small_fixed' && j.budget_or_estimate) return `Target $${j.budget_or_estimate}`;
  if (j.pricing_type === 'hourly' && j.budget_or_estimate) return `~${j.budget_or_estimate} hrs`;
  if (j.budget_min || j.budget_max) return `Budget $${j.budget_min || 0}–${j.budget_max || '?'}`;
  return 'Quote required';
};

const fmtDate = (d) => (d ? new Date(`${d.slice(0, 10)}T00:00:00`).toLocaleDateString('en-NZ', { weekday: 'short', day: 'numeric', month: 'short' }) : null);

function JobMeta({ job }) {
  const size = SIZE_META[job.pricing_type] || SIZE_META.large_quote;
  const SizeIcon = size.icon;
  const TrackIcon = job.service_type === 'commercial' ? Building2 : HomeIcon;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground mt-2">
      <Badge className={`${size.cls} border-0 gap-1`}><SizeIcon className="w-3 h-3" /> {size.l}</Badge>
      <span className="inline-flex items-center gap-1 capitalize"><TrackIcon className="w-3 h-3" /> {job.service_type}</span>
      <span className="font-medium text-foreground">{priceLine(job)}</span>
      {job.location && <span className="inline-flex items-center gap-1 min-w-0"><MapPin className="w-3 h-3 shrink-0" /> <span className="truncate max-w-[220px]">{job.location}</span></span>}
      {job.preferred_date && <span className="inline-flex items-center gap-1"><CalendarDays className="w-3 h-3" /> {fmtDate(job.preferred_date)}</span>}
    </div>
  );
}

export default function MatchedJobsFeed() {
  const [matches, setMatches] = useState(null);
  const [dialog, setDialog] = useState(null); // { match, kind: 'accept' | 'quote' }
  const [form, setForm] = useState({ message: '', amount: '', available_from: '' });
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.get('/matches/mine').then((r) => setMatches(r.data || [])).catch(() => setMatches([]));
  }, []);
  useEffect(() => { load(); }, [load]);

  const open = (match, kind) => { setForm({ message: '', amount: '', available_from: match.job.preferred_date || '' }); setDialog({ match, kind }); };

  const submit = async () => {
    const { match, kind } = dialog;
    if (kind === 'quote' && !(Number(form.amount) > 0)) { toast.error('Enter your fixed quote'); return; }
    setBusy(true);
    try {
      if (kind === 'quote') await api.post(`/matches/${match.match_id}/quote`, { amount: Number(form.amount), message: form.message });
      else await api.post(`/matches/${match.match_id}/accept`, { message: form.message, available_from: form.available_from || null });
      toast.success(kind === 'quote' ? 'Quote sent to the client' : 'Accepted — the client will confirm who gets the job');
      setDialog(null);
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Something went wrong');
    } finally { setBusy(false); }
  };

  const decline = async (m) => {
    try { await api.post(`/matches/${m.match_id}/decline`); toast.success('Job declined'); load(); }
    catch (err) { toast.error(err?.response?.data?.detail || 'Could not decline'); }
  };
  const progress = async (m, status) => {
    try { await api.post(`/jobs/${m.job_id}/progress`, { status }); toast.success(status === 'done' ? 'Job marked complete' : 'Job started'); load(); }
    catch (err) { toast.error(err?.response?.data?.detail || 'Could not update'); }
  };

  if (matches === null) return <div className="py-8 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;

  const isOpenJob = (m) => ['open', 'matched'].includes(m.job.status);
  const fresh = matches.filter((m) => m.match_status === 'notified' && isOpenJob(m));
  const waiting = matches.filter((m) => ['accepted', 'quote_submitted'].includes(m.match_status) && isOpenJob(m));
  const active = matches.filter((m) => m.match_status === 'awarded' && ['assigned', 'in_progress'].includes(m.job.status));

  return (
    <div className="space-y-6" data-testid="matched-jobs-feed">
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Zap className="w-4 h-4 text-primary" />
          <h2 className="font-semibold text-foreground">New Matched Jobs</h2>
          {fresh.length > 0 && <Badge className="bg-primary text-primary-foreground" data-testid="matched-new-count">{fresh.length}</Badge>}
        </div>
        <div className="space-y-2">
          {fresh.map((m) => (
            <div key={m.match_id} className="bg-card border border-primary/30 rounded-xl p-4" data-testid={`match-card-${m.match_id}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <Link to={`/jobs/${m.job_id}`} className="font-semibold text-foreground hover:text-primary">{m.job.title}</Link>
                  <div className="text-xs text-muted-foreground">{m.job.subcategory_name || m.job.subcategory || m.job.category}</div>
                  {m.job.description && <div className="text-sm text-muted-foreground line-clamp-2 mt-1">{m.job.description}</div>}
                </div>
              </div>
              <JobMeta job={m.job} />
              <div className="flex gap-2 mt-3">
                {m.job.pricing_type === 'large_quote' ? (
                  <Button size="sm" onClick={() => open(m, 'quote')} data-testid={`match-quote-${m.match_id}`}><ClipboardList className="w-3.5 h-3.5 mr-1" /> Submit Quote</Button>
                ) : (
                  <Button size="sm" onClick={() => open(m, 'accept')} data-testid={`match-accept-${m.match_id}`}><CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Accept &amp; Claim Job</Button>
                )}
                <Button size="sm" variant="ghost" onClick={() => decline(m)} data-testid={`match-decline-${m.match_id}`}><X className="w-3.5 h-3.5 mr-1" /> Decline</Button>
              </div>
            </div>
          ))}
          {fresh.length === 0 && (
            <div className="text-sm text-muted-foreground text-center py-8 bg-card border border-dashed border-border rounded-xl" data-testid="matched-empty">
              No new matched jobs yet — we'll alert you when a job fits your specializations.
            </div>
          )}
        </div>
      </section>

      {waiting.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3"><Hourglass className="w-4 h-4 text-amber-500" /><h2 className="font-semibold text-foreground">Waiting for the client</h2></div>
          <div className="space-y-2">
            {waiting.map((m) => (
              <Link to={`/jobs/${m.job_id}`} key={m.match_id} className="block bg-card border border-border rounded-xl p-4 hover:border-primary/40" data-testid={`match-waiting-${m.match_id}`}>
                <div className="flex items-center justify-between gap-3">
                  <div className="font-medium text-foreground truncate">{m.job.title}</div>
                  <Badge variant="outline" className="shrink-0">{m.match_status === 'quote_submitted' ? `Quoted $${m.quote_amount}` : 'Accepted'}</Badge>
                </div>
                <JobMeta job={m.job} />
              </Link>
            ))}
          </div>
        </section>
      )}

      <section>
        <div className="flex items-center gap-2 mb-3"><CheckCircle2 className="w-4 h-4 text-emerald-500" /><h2 className="font-semibold text-foreground">Active assigned jobs</h2></div>
        <div className="space-y-2">
          {active.map((m) => (
            <div key={m.match_id} className="bg-card border border-emerald-500/30 rounded-xl p-4" data-testid={`match-active-${m.match_id}`}>
              <div className="flex items-center justify-between gap-3">
                <Link to={`/jobs/${m.job_id}`} className="font-semibold text-foreground hover:text-primary truncate">{m.job.title}</Link>
                <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 border-0 shrink-0">{m.job.status === 'in_progress' ? 'In progress' : 'Assigned'}</Badge>
              </div>
              <JobMeta job={m.job} />
              <div className="flex gap-2 mt-3">
                {m.job.status === 'assigned' && <Button size="sm" onClick={() => progress(m, 'in_progress')} data-testid={`match-start-${m.match_id}`}><Play className="w-3.5 h-3.5 mr-1" /> Start job</Button>}
                <Button size="sm" variant={m.job.status === 'in_progress' ? 'default' : 'outline'} onClick={() => progress(m, 'done')} data-testid={`match-complete-${m.match_id}`}><CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Mark complete</Button>
              </div>
            </div>
          ))}
          {active.length === 0 && <div className="text-sm text-muted-foreground text-center py-6">No active assigned jobs</div>}
        </div>
      </section>

      <Dialog open={!!dialog} onOpenChange={(o) => !o && setDialog(null)}>
        <DialogContent className="max-w-md" data-testid="match-respond-dialog">
          <DialogHeader>
            <DialogTitle>{dialog?.kind === 'quote' ? 'Submit a fixed quote' : 'Accept & claim this job'}</DialogTitle>
            <DialogDescription>{dialog?.match.job.title} · {dialog && priceLine(dialog.match.job)}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {dialog?.kind === 'quote' ? (
              <div>
                <Label>Your fixed quote ($)</Label>
                <Input type="number" min="1" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} className="mt-1.5" data-testid="match-quote-amount" placeholder="e.g. 2400" />
              </div>
            ) : (
              <div>
                <Label>Available from</Label>
                <Input type="date" min={new Date().toISOString().slice(0, 10)} value={form.available_from} onChange={(e) => setForm({ ...form, available_from: e.target.value })} className="mt-1.5" data-testid="match-available-from" />
              </div>
            )}
            <div>
              <Label>Message to the client <span className="text-muted-foreground font-normal">(optional)</span></Label>
              <Textarea rows={3} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} className="mt-1.5" data-testid="match-message" placeholder={dialog?.kind === 'quote' ? "What's included, timeline, materials…" : 'When you can come, anything they should know…'} />
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => setDialog(null)}>Cancel</Button>
              <Button className="flex-1" onClick={submit} disabled={busy} data-testid="match-respond-submit">
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : dialog?.kind === 'quote' ? 'Send quote' : 'Accept job'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
