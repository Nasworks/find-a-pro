import React, { useCallback, useEffect, useState } from 'react';
import { Users, Star, ShieldCheck, Trophy, Loader2, Hourglass, CalendarDays, MessageSquare } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import api from '../lib/api';
import { BadgeCheck } from 'lucide-react';
import { toast } from 'sonner';

const SIZE_LABEL = { solo: 'Solo operator', small_team: 'Small team', medium_enterprise: 'Medium business' };

/** Client view of the dispatch queue: how many specialised pros were notified, their responses, and Award. */
export default function JobMatchesPanel({ job, onAwarded }) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = useCallback(() => {
    api.get(`/jobs/${job.job_id}/matches`).then((r) => setData(r.data)).catch(() => setData(null));
  }, [job.job_id]);
  useEffect(() => { load(); }, [load, job.status]);

  const award = async (m) => {
    setBusy(m.match_id);
    try {
      const r = await api.post(`/jobs/${job.job_id}/award`, { match_id: m.match_id });
      toast.success(`Job awarded to ${m.provider?.business_name || m.provider_name} — $${r.data.amount}`);
      onAwarded?.();
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not award the job');
    } finally { setBusy(null); }
  };

  if (!data) return null;
  const canAward = ['open', 'matched'].includes(job.status);
  const responses = data.matches.filter((m) => ['accepted', 'quote_submitted', 'awarded'].includes(m.match_status));
  const waitingCount = data.matches.filter((m) => m.match_status === 'notified').length;

  return (
    <div className="bg-card border border-border rounded-2xl p-5" data-testid="job-matches-panel">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-primary" />
          <span className="font-semibold text-foreground">Matched pros</span>
        </div>
        <div className="flex gap-2 text-xs">
          <Badge variant="outline" data-testid="job-matches-notified">{data.notified} specialised pro{data.notified === 1 ? '' : 's'} notified</Badge>
          <Badge variant="outline" data-testid="job-matches-responded">{data.responded} responded</Badge>
        </div>
      </div>

      {data.notified === 0 && (
        <p className="text-sm text-muted-foreground mt-3">No pros with this exact specialization yet — your job is still on the open job board for every pro to bid.</p>
      )}

      <div className="space-y-2 mt-4">
        {responses.map((m) => {
          const p = m.provider || {};
          const won = m.match_status === 'awarded';
          return (
            <div key={m.match_id} className={`p-4 rounded-xl border ${won ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-border'}`} data-testid={`job-match-${m.match_id}`}>
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-foreground">{p.business_name || m.provider_name}</span>
                    {p.qualified_verified && <span className="inline-flex items-center gap-0.5 text-[11px] text-emerald-600"><BadgeCheck className="w-3.5 h-3.5" /> Qualified</span>}
                    {p.police_checked && <span className="inline-flex items-center gap-0.5 text-[11px] text-emerald-600"><ShieldCheck className="w-3.5 h-3.5" /> Police checked</span>}
                    {won && <Badge className="bg-emerald-600 text-white border-0 gap-1"><Trophy className="w-3 h-3" /> Awarded</Badge>}
                  </div>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground mt-1">
                    {p.rating ? <span className="inline-flex items-center gap-1"><Star className="w-3 h-3 text-amber-500 fill-amber-500" /> {p.rating} ({p.reviews_count || 0})</span> : null}
                    {p.business_size && <span>{SIZE_LABEL[p.business_size]}</span>}
                    {p.availability_status === 'busy' && <span className="text-amber-600">Busy</span>}
                    {m.available_from && <span className="inline-flex items-center gap-1"><CalendarDays className="w-3 h-3" /> From {m.available_from}</span>}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  {m.match_status === 'quote_submitted' || m.quote_amount ? (
                    <div className="text-lg font-bold text-foreground" data-testid={`job-match-amount-${m.match_id}`}>${m.quote_amount}</div>
                  ) : !won ? (
                    <Badge variant="outline">Accepted</Badge>
                  ) : null}
                </div>
              </div>
              {m.message && <div className="text-sm text-muted-foreground mt-2 flex gap-1.5"><MessageSquare className="w-3.5 h-3.5 mt-0.5 shrink-0" /> {m.message}</div>}
              {canAward && (
                <Button size="sm" className="mt-3" onClick={() => award(m)} disabled={!!busy} data-testid={`job-match-award-${m.match_id}`}>
                  {busy === m.match_id ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Trophy className="w-3.5 h-3.5 mr-1" /> Award job</>}
                </Button>
              )}
            </div>
          );
        })}
        {canAward && responses.length === 0 && waitingCount > 0 && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground"><Hourglass className="w-4 h-4" /> Waiting for {waitingCount} matched pro{waitingCount === 1 ? '' : 's'} to respond…</div>
        )}
      </div>
    </div>
  );
}
