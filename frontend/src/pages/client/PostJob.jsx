import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, MapPin, Loader2 } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { RadioGroup, RadioGroupItem } from '../../components/ui/radio-group';
import api from '../../lib/api';
import { toast } from 'sonner';

export default function PostJob() {
  const location = useLocation();
  const navigate = useNavigate();
  const preset = location.state || {};
  const [categories, setCategories] = useState([]);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    title: '',
    description: preset.description || '',
    category: preset.category || '',
    location: 'Auckland',
    budget_min: '',
    budget_max: '',
    urgency: 'flexible',
    mode: preset.mode || 'quotes',
    photos: [],
  });

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    api.get('/categories').then((r) => setCategories(r.data));
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.title || !form.category) { toast.error('Please fill in title and category'); return; }
    setSaving(true);
    try {
      const payload = {
        ...form,
        budget_min: form.budget_min ? Number(form.budget_min) : null,
        budget_max: form.budget_max ? Number(form.budget_max) : null,
      };
      const res = await api.post('/jobs', payload);
      toast.success('Job posted — pros will be notified');
      navigate(`/jobs/${res.data.job_id}`);
    } catch {
      toast.error('Failed to post job');
    } finally { setSaving(false); }
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-4 h-4" /> Back
      </button>
      <h1 className="text-3xl font-bold text-foreground">Post a Job</h1>
      <p className="text-muted-foreground mt-1">Tell us the details — we'll match you with the right pros.</p>

      <form onSubmit={submit} className="mt-8 space-y-5 bg-card border border-border rounded-2xl p-6">
        <div>
          <Label>Job title</Label>
          <Input value={form.title} onChange={(e) => update('title', e.target.value)} placeholder="e.g. Fix leaking kitchen tap" required className="mt-1.5" />
        </div>

        <div>
          <Label>Category</Label>
          <Select value={form.category} onValueChange={(v) => update('category', v)}>
            <SelectTrigger className="mt-1.5"><SelectValue placeholder="Choose a category" /></SelectTrigger>
            <SelectContent>
              {categories.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label>Description</Label>
          <Textarea value={form.description} onChange={(e) => update('description', e.target.value)} rows={4} placeholder="Describe the problem or work needed" required className="mt-1.5" />
        </div>

        <div>
          <Label>Location</Label>
          <div className="relative mt-1.5">
            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input value={form.location} onChange={(e) => update('location', e.target.value)} className="pl-9" />
          </div>
        </div>

        <div>
          <Label>Urgency</Label>
          <RadioGroup value={form.urgency} onValueChange={(v) => update('urgency', v)} className="mt-2 grid grid-cols-2 gap-2">
            {[
              { v: 'asap', l: 'ASAP - Urgent' },
              { v: 'this_week', l: 'Within 1 week' },
              { v: 'within_month', l: 'Within a month' },
              { v: 'flexible', l: 'Flexible' },
            ].map((o) => (
              <label key={o.v} className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-colors ${form.urgency === o.v ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}>
                <RadioGroupItem value={o.v} id={o.v} />
                <span className="text-sm text-foreground">{o.l}</span>
              </label>
            ))}
          </RadioGroup>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Budget min ($)</Label>
            <Input type="number" value={form.budget_min} onChange={(e) => update('budget_min', e.target.value)} placeholder="0" className="mt-1.5" />
          </div>
          <div>
            <Label>Budget max ($)</Label>
            <Input type="number" value={form.budget_max} onChange={(e) => update('budget_max', e.target.value)} placeholder="0" className="mt-1.5" />
          </div>
        </div>

        <div>
          <Label>How would you like to receive offers?</Label>
          <RadioGroup value={form.mode} onValueChange={(v) => update('mode', v)} className="mt-2 space-y-2">
            {[
              { v: 'instant', l: 'Instant Booking', d: 'First nearby pro accepts' },
              { v: 'quotes', l: 'Get 3 Quotes', d: 'Compare & chat with 3 pros' },
              { v: 'bids', l: 'Open Bidding', d: 'Public job — receive multiple bids' },
            ].map((o) => (
              <label key={o.v} className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${form.mode === o.v ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}>
                <RadioGroupItem value={o.v} id={`mode-${o.v}`} className="mt-0.5" />
                <div>
                  <div className="text-sm font-medium text-foreground">{o.l}</div>
                  <div className="text-xs text-muted-foreground">{o.d}</div>
                </div>
              </label>
            ))}
          </RadioGroup>
        </div>

        <div className="flex gap-3 pt-2">
          <Button type="button" variant="outline" onClick={() => navigate(-1)} className="flex-1">Cancel</Button>
          <Button type="submit" disabled={saving} className="flex-1">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Post Job'}
          </Button>
        </div>
      </form>
    </div>
  );
}
