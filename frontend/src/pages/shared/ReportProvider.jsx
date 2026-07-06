import React, { useState } from 'react';
import { Flag, AlertTriangle } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';

export default function ReportProvider() {
  const [form, setForm] = useState({ provider_name: '', reason: 'poor_workmanship', description: '' });

  const submit = (e) => {
    e.preventDefault();
    if (!form.provider_name || !form.description) { toast.error('Please fill in provider name and description'); return; }
    toast.success('Report submitted. We\u2019ll review within 24 hours.');
    setForm({ provider_name: '', reason: 'poor_workmanship', description: '' });
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2"><Flag className="w-5 h-5 text-rose-500" /> Report a Provider</h1>
        <p className="text-sm text-muted-foreground">Help us keep Dispatchr safe. All reports are confidential.</p>
      </div>

      <div className="bg-amber-50 border border-amber-200 dark:bg-amber-950/40 dark:border-amber-800 rounded-2xl p-4 mb-6 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-sm">
          <div className="font-semibold text-foreground">Before you report</div>
          <p className="text-muted-foreground mt-1">For a warranty issue or price dispute, try filing a Warranty Claim or Dispute first — those get resolved in 5 business days.</p>
        </div>
      </div>

      <form onSubmit={submit} className="space-y-4 bg-card border border-border rounded-2xl p-6">
        <div>
          <Label>Provider name</Label>
          <Input value={form.provider_name} onChange={(e) => setForm({ ...form, provider_name: e.target.value })} placeholder="e.g. Sarah Chen Plumbing" className="mt-1.5" />
        </div>
        <div>
          <Label>Reason for reporting</Label>
          <Select value={form.reason} onValueChange={(v) => setForm({ ...form, reason: v })}>
            <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="poor_workmanship">Poor workmanship</SelectItem>
              <SelectItem value="no_show">No-show / abandoned job</SelectItem>
              <SelectItem value="unsafe">Unsafe practices / H&S concern</SelectItem>
              <SelectItem value="unlicensed">Unlicensed / uninsured</SelectItem>
              <SelectItem value="rude">Rude / unprofessional</SelectItem>
              <SelectItem value="scam">Fraud or scam</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>What happened?</Label>
          <Textarea rows={5} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Please provide as much detail as possible. Include dates, photos or invoice numbers if available." className="mt-1.5" />
        </div>
        <Button type="submit" className="w-full">Submit report</Button>
      </form>
    </div>
  );
}
