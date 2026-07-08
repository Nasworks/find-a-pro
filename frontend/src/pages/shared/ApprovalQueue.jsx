import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCheck, Clock, X, Check, Loader2, User, DollarSign, MapPin, Sparkles } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../../components/ui/dialog';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';
import api from '../../lib/api';
import { extractError } from '../../lib/errors';

const URGENCY_MAP = {
  asap: { label: 'ASAP', cls: 'bg-rose-100 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300' },
  this_week: { label: 'This week', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300' },
  within_month: { label: 'Within a month', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300' },
  flexible: { label: 'Flexible', cls: 'bg-muted text-muted-foreground' },
};

export default function ApprovalQueue() {
  const [queue, setQueue] = useState([]);
  const [preferredProviders, setPreferredProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const [action, setAction] = useState(null); // 'approve' | 'reject'
  const [busy, setBusy] = useState(false);
  const [assignedProviderId, setAssignedProviderId] = useState('');
  const [openToBids, setOpenToBids] = useState(true);
  const [reason, setReason] = useState('');
  const navigate = useNavigate();

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      api.get('/approvals/queue'),
      api.get('/approvals/preferred-providers').catch(() => ({ data: [] })),
    ])
      .then(([q, p]) => {
        setQueue(q.data);
        setPreferredProviders(p.data);
      })
      .catch((err) => toast.error(extractError(err, 'Failed to load')))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const openAction = (job, verb) => {
    setSelectedJob(job);
    setAction(verb);
    setAssignedProviderId('');
    setOpenToBids(true);
    setReason('');
  };

  const submit = async () => {
    if (!selectedJob) return;
    setBusy(true);
    try {
      const url = `/jobs/${selectedJob.job_id}/${action}`;
      const body = action === 'reject'
        ? { reason }
        : { assigned_provider_id: assignedProviderId || null, open_to_bids: openToBids };
      await api.post(url, body);
      toast.success(action === 'approve' ? 'Job approved and open to providers' : 'Request rejected');
      setSelectedJob(null);
      setAction(null);
      load();
    } catch (err) {
      toast.error(extractError(err, 'Failed'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6" data-testid="approval-queue-page">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-foreground">Approval Queue</h1>
        <p className="text-muted-foreground mt-1">Maintenance requests from your tenants awaiting your decision.</p>
      </div>

      <StatBar count={queue.length} />

      {loading ? (
        <div className="flex items-center justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
      ) : queue.length === 0 ? (
        <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center mt-6">
          <CheckCheck className="w-10 h-10 mx-auto text-emerald-500 opacity-70 mb-3" />
          <div className="font-medium text-foreground">All caught up</div>
          <p className="text-sm text-muted-foreground mt-1">No pending requests. When your tenants raise maintenance issues, they&apos;ll appear here for approval.</p>
        </div>
      ) : (
        <div className="mt-6 space-y-3">
          {queue.map((j) => (
            <RequestCard key={j.job_id} job={j} onApprove={() => openAction(j, 'approve')} onReject={() => openAction(j, 'reject')} onView={() => navigate(`/jobs/${j.job_id}`)} />
          ))}
        </div>
      )}

      <Dialog open={!!selectedJob} onOpenChange={(v) => { if (!v) setSelectedJob(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{action === 'approve' ? 'Approve request' : 'Reject request'}</DialogTitle>
            <DialogDescription>
              {action === 'approve'
                ? 'Choose how this request should be handled. Quotes and invoices will be billed to you.'
                : 'Let your tenant know why. This will close the request.'}
            </DialogDescription>
          </DialogHeader>
          {action === 'approve' ? (
            <div className="space-y-4 mt-2">
              <div className="rounded-xl border border-border p-3 bg-muted/30">
                <div className="text-xs text-muted-foreground">Request</div>
                <div className="font-medium text-foreground">{selectedJob?.title}</div>
              </div>
              <div>
                <Label>Assign a preferred provider (optional)</Label>
                <Select value={assignedProviderId} onValueChange={setAssignedProviderId}>
                  <SelectTrigger data-testid="assign-provider-select" className="mt-1.5"><SelectValue placeholder="Open to any provider" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__any__">Any provider (open to bids)</SelectItem>
                    {preferredProviders.map((p) => (
                      <SelectItem key={p.user_id} value={p.user_id}>{p.business_name} ({p.rating?.toFixed?.(1)}★)</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {preferredProviders.length === 0 && (
                  <p className="text-xs text-muted-foreground mt-1">You have no preferred providers yet — they&apos;ll appear here after you accept bids from them on other jobs.</p>
                )}
              </div>
              {assignedProviderId && assignedProviderId !== '__any__' && (
                <label className="flex items-center gap-2 text-sm text-muted-foreground">
                  <input type="checkbox" data-testid="open-to-bids-checkbox" checked={openToBids} onChange={(e) => setOpenToBids(e.target.checked)} className="rounded" />
                  Also allow other providers to bid
                </label>
              )}
            </div>
          ) : (
            <div className="space-y-3 mt-2">
              <div className="rounded-xl border border-border p-3 bg-muted/30">
                <div className="text-xs text-muted-foreground">Request</div>
                <div className="font-medium text-foreground">{selectedJob?.title}</div>
              </div>
              <div>
                <Label>Reason (visible to tenant)</Label>
                <Textarea
                  data-testid="reject-reason-input"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  rows={3}
                  placeholder="e.g. Not urgent — we'll revisit next quarter"
                  className="mt-1.5"
                  required
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedJob(null)}>Cancel</Button>
            <Button
              data-testid={`submit-${action}`}
              onClick={submit}
              disabled={busy || (action === 'reject' && reason.trim().length < 3)}
              className={action === 'reject' ? 'bg-rose-600 hover:bg-rose-700' : 'bg-emerald-600 hover:bg-emerald-700'}
            >
              {busy ? <Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> : action === 'approve' ? <Check className="w-4 h-4 mr-1.5" /> : <X className="w-4 h-4 mr-1.5" />}
              {action === 'approve' ? 'Approve' : 'Reject'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatBar({ count }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="rounded-2xl bg-gradient-to-br from-primary/10 to-blue-500/5 border border-primary/20 p-4">
        <div className="text-2xl font-bold text-foreground">{count}</div>
        <div className="text-xs text-muted-foreground uppercase tracking-wider">Pending decisions</div>
      </div>
      <div className="rounded-2xl bg-card border border-border p-4">
        <div className="text-2xl font-bold text-foreground">—</div>
        <div className="text-xs text-muted-foreground uppercase tracking-wider">Approved this month</div>
      </div>
      <div className="rounded-2xl bg-card border border-border p-4">
        <div className="text-2xl font-bold text-foreground">—</div>
        <div className="text-xs text-muted-foreground uppercase tracking-wider">Avg spend / month</div>
      </div>
    </div>
  );
}

function RequestCard({ job, onApprove, onReject, onView }) {
  const urg = URGENCY_MAP[job.urgency] || URGENCY_MAP.flexible;
  return (
    <div className="bg-card border border-border rounded-2xl p-4 hover:border-primary/40 transition-colors" data-testid={`approval-card-${job.job_id}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground mb-1">
            <span className="inline-flex items-center gap-1"><User className="w-3 h-3" /> {job.tenant?.name || 'Tenant'}</span>
            {job.location && <><span>·</span><span className="inline-flex items-center gap-1"><MapPin className="w-3 h-3" /> {job.location}</span></>}
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${urg.cls}`}><Clock className="w-2.5 h-2.5 inline mr-0.5" /> {urg.label}</span>
          </div>
          <h3 className="font-semibold text-foreground">{job.title}</h3>
          <p className="mt-1 text-sm text-muted-foreground line-clamp-2">{job.description}</p>
          {(job.budget_min || job.budget_max) && (
            <div className="mt-2 inline-flex items-center gap-1 text-xs text-muted-foreground"><DollarSign className="w-3 h-3" /> Budget: ${job.budget_min || 0} – ${job.budget_max || '—'}</div>
          )}
        </div>
        <div className="flex flex-col gap-1.5 shrink-0">
          <Button data-testid={`approve-${job.job_id}`} size="sm" onClick={onApprove} className="bg-emerald-600 hover:bg-emerald-700">
            <Check className="w-3.5 h-3.5 mr-1" /> Approve
          </Button>
          <Button data-testid={`reject-${job.job_id}`} size="sm" variant="outline" onClick={onReject}>
            <X className="w-3.5 h-3.5 mr-1" /> Reject
          </Button>
          <Button size="sm" variant="ghost" onClick={onView}><Sparkles className="w-3.5 h-3.5 mr-1" /> View</Button>
        </div>
      </div>
    </div>
  );
}
