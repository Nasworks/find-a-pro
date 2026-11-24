import React, { useEffect, useState } from 'react';
import { Loader2, Send } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import api from '../../lib/api';

const empty = { job_id: '', title: '', address: '', notes: '', scheduled_for: '' };

export const SendJobDialog = ({ member, onClose, onDone }) => {
  const [jobs, setJobs] = useState([]);
  const [form, setForm] = useState(empty);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!member) return;
    setForm(empty);
    api.get('/team/jobs').then((r) => setJobs(r.data)).catch(() => setJobs([]));
  }, [member]);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const send = async () => {
    setBusy(true);
    try {
      await api.post('/team/assignments', { ...form, member_id: member.member_id, job_id: form.job_id || null, scheduled_for: form.scheduled_for || null });
      toast.success(`Job sent to ${member.name}`);
      onDone();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not send job');
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={!!member} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="send-job-dialog">
        <DialogHeader>
          <DialogTitle>Send a job to {member?.name}</DialogTitle>
          <DialogDescription>Pick one of your booked jobs, or type in a job of your own.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Booked job</Label>
            <select value={form.job_id} onChange={set('job_id')} data-testid="send-job-select" className="mt-1.5 w-full h-10 rounded-md border border-input bg-background px-3 text-sm">
              <option value="">Other job (type below)</option>
              {jobs.map((j) => <option key={j.job_id} value={j.job_id}>{j.title} · {j.location || j.address || ''}</option>)}
            </select>
          </div>
          {!form.job_id && (
            <>
              <div><Label>Job title</Label><Input value={form.title} onChange={set('title')} placeholder="e.g. Replace hot water cylinder" className="mt-1.5" data-testid="send-job-title" /></div>
              <div><Label>Site address</Label><Input value={form.address} onChange={set('address')} placeholder="e.g. 12 Ponsonby Rd, Auckland" className="mt-1.5" data-testid="send-job-address" /></div>
            </>
          )}
          <div><Label>When</Label><Input type="datetime-local" value={form.scheduled_for} onChange={set('scheduled_for')} className="mt-1.5" data-testid="send-job-when" /></div>
          <div><Label>Notes for the worker</Label><Textarea value={form.notes} onChange={set('notes')} rows={3} placeholder="Gate code, tools to bring..." className="mt-1.5" data-testid="send-job-notes" /></div>
          <Button onClick={send} disabled={busy || (!form.job_id && !form.title.trim())} className="w-full" data-testid="send-job-submit">
            {busy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />} Send job
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default SendJobDialog;
