import React, { useEffect, useState } from 'react';
import { Plus, Briefcase, MapPin, DollarSign, Clock } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import api from '../../lib/api';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';

const trades = ['electrician', 'plumber', 'chippie', 'painter', 'labourer', 'gib_stopper', 'roofer', 'tiler'];

export default function TradesBoard() {
  const [jobs, setJobs] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', trade: 'electrician', location: 'Auckland', budget: '', urgency: 'this_week' });

  const load = async () => {
    const r = await api.get('/trades-board');
    setJobs(r.data);
  };
  useEffect(() => { load(); }, []);

  const submit = async () => {
    if (!form.title) return;
    await api.post('/trades-board', { ...form, budget: form.budget ? Number(form.budget) : null });
    toast.success('Trade job posted');
    setOpen(false);
    setForm({ title: '', description: '', trade: 'electrician', location: 'Auckland', budget: '', urgency: 'this_week' });
    load();
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Trades Board</h1>
          <p className="text-sm text-muted-foreground">Post to hire other trades, or pick up subcontract work</p>
        </div>
        <Button onClick={() => setOpen(true)}><Plus className="w-4 h-4 mr-1" /> Post Trade Job</Button>
      </div>

      {jobs.length === 0 ? (
        <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
          <Briefcase className="w-10 h-10 mx-auto text-muted-foreground mb-3 opacity-40" />
          <div className="font-medium text-foreground">No trade jobs posted</div>
          <p className="text-sm text-muted-foreground mt-1">Providers post here when they need to hire other tradies (sparkies, plumbers, chippies etc.)</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {jobs.map((j) => (
            <div key={j.trade_job_id} className="bg-card border border-border rounded-2xl p-5 hover:border-primary/40 transition-colors">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <Badge className="capitalize bg-violet-100 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300">{j.trade.replace('_', ' ')}</Badge>
                    <Badge variant="secondary" className="capitalize">{j.urgency.replace('_', ' ')}</Badge>
                  </div>
                  <h3 className="font-semibold text-foreground mt-2">{j.title}</h3>
                </div>
                {j.budget && <div className="text-lg font-bold text-primary">${j.budget}</div>}
              </div>
              <p className="text-sm text-muted-foreground mt-2 line-clamp-2">{j.description}</p>
              <div className="flex flex-wrap gap-3 mt-3 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1"><MapPin className="w-3 h-3" /> {j.location}</span>
                <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" /> {formatDistanceToNow(new Date(j.created_at), { addSuffix: true })}</span>
                <span>· by {j.poster_name}</span>
              </div>
              <Button size="sm" className="w-full mt-4">Contact Poster</Button>
            </div>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Post trade job</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-2">
            <div><Label>Title</Label><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g. Need sparky for switchboard upgrade" className="mt-1.5" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Trade needed</Label>
                <Select value={form.trade} onValueChange={(v) => setForm({ ...form, trade: v })}>
                  <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                  <SelectContent>{trades.map((t) => <SelectItem key={t} value={t} className="capitalize">{t.replace('_', ' ')}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label>Urgency</Label>
                <Select value={form.urgency} onValueChange={(v) => setForm({ ...form, urgency: v })}>
                  <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="asap">ASAP</SelectItem>
                    <SelectItem value="this_week">This week</SelectItem>
                    <SelectItem value="within_month">Within a month</SelectItem>
                    <SelectItem value="flexible">Flexible</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div><Label>Description</Label><Textarea rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="mt-1.5" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Location</Label><Input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} className="mt-1.5" /></div>
              <div><Label>Budget ($)</Label><Input type="number" value={form.budget} onChange={(e) => setForm({ ...form, budget: e.target.value })} className="mt-1.5" /></div>
            </div>
            <Button onClick={submit} className="w-full">Post to board</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
