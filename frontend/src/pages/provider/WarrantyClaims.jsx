import React, { useEffect, useState } from 'react';
import { Shield, Plus, AlertCircle } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import api from '../../lib/api';
import { toast } from 'sonner';

const statusColors = {
  open: 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300',
  in_review: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
  resolved: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300',
  denied: 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300',
};

export default function WarrantyClaims() {
  const [claims, setClaims] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ subject: '', description: '', provider_name: '' });

  const load = async () => {
    const r = await api.get('/warranty-claims/mine');
    setClaims(r.data);
  };
  useEffect(() => { load(); }, []);

  const submit = async () => {
    if (!form.subject || !form.description) return;
    await api.post('/warranty-claims', form);
    toast.success('Claim submitted');
    setOpen(false);
    setForm({ subject: '', description: '', provider_name: '' });
    load();
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Warranty Claims</h1>
          <p className="text-sm text-muted-foreground">Report issues with completed jobs · All jobs covered 12-month minimum</p>
        </div>
        <Button onClick={() => setOpen(true)}><Plus className="w-4 h-4 mr-1" /> New Claim</Button>
      </div>

      <div className="bg-primary/5 border border-primary/20 rounded-2xl p-4 mb-6 flex items-start gap-3">
        <Shield className="w-5 h-5 text-primary shrink-0 mt-0.5" />
        <div className="text-sm">
          <div className="font-semibold text-foreground">Dispatchr Warranty Protection</div>
          <p className="text-muted-foreground mt-1">All jobs booked through Dispatchr include workmanship warranty. If something&apos;s not right, we&apos;ll mediate resolution within 5 business days.</p>
        </div>
      </div>

      {claims.length === 0 ? (
        <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
          <Shield className="w-10 h-10 mx-auto text-muted-foreground mb-3 opacity-40" />
          <div className="font-medium text-foreground">No claims filed</div>
          <p className="text-sm text-muted-foreground mt-1">Great news — no issues to report!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {claims.map((c) => (
            <div key={c.claim_id} className="bg-card border border-border rounded-2xl p-5">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-amber-100 text-amber-600 dark:bg-amber-950/60 dark:text-amber-300 flex items-center justify-center"><AlertCircle className="w-5 h-5" /></div>
                  <div>
                    <div className="font-semibold text-foreground">{c.subject}</div>
                    <div className="text-xs text-muted-foreground">{c.provider_name || 'Provider'} · Filed {new Date(c.created_at).toLocaleDateString()}</div>
                  </div>
                </div>
                <Badge className={statusColors[c.status]}>{c.status.replace('_', ' ')}</Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-3">{c.description}</p>
            </div>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>File warranty claim</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-2">
            <div><Label>Subject</Label><Input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} placeholder="e.g. Bathroom tiles cracked" className="mt-1.5" /></div>
            <div><Label>Provider name</Label><Input value={form.provider_name} onChange={(e) => setForm({ ...form, provider_name: e.target.value })} placeholder="Who did the work?" className="mt-1.5" /></div>
            <div><Label>Describe the issue</Label><Textarea rows={4} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Please provide as much detail as possible..." className="mt-1.5" /></div>
            <Button onClick={submit} className="w-full">Submit claim</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
