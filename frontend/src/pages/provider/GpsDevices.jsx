import React, { useEffect, useState } from 'react';
import { Plus, Radio, Battery, MapPin, Signal } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import api from '../../lib/api';
import { toast } from 'sonner';

export default function GpsDevices() {
  const [devices, setDevices] = useState([]);
  const [members, setMembers] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: '', assigned_to: '' });

  const load = async () => {
    const [d, m] = await Promise.all([api.get('/gps-devices'), api.get('/team')]);
    setDevices(d.data);
    setMembers(m.data);
  };
  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!form.name) return;
    await api.post('/gps-devices', form);
    toast.success('Device added');
    setOpen(false);
    setForm({ name: '', assigned_to: '' });
    load();
  };

  const nameOf = (memberId) => members.find((m) => m.member_id === memberId)?.name || 'Unassigned';

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">GPS Devices</h1>
          <p className="text-sm text-muted-foreground">Manage vehicle & tool trackers</p>
        </div>
        <Button onClick={() => setOpen(true)}><Plus className="w-4 h-4 mr-1" /> Add Device</Button>
      </div>

      {devices.length === 0 ? (
        <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
          <Radio className="w-10 h-10 mx-auto text-muted-foreground mb-3 opacity-40" />
          <div className="font-medium text-foreground">No devices registered</div>
          <p className="text-sm text-muted-foreground mt-1">Add GPS trackers for vehicles, tools or workers.</p>
          <div className="mt-4 text-xs text-muted-foreground">Pro plan includes 2 devices · Enterprise unlimited</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {devices.map((d) => (
            <div key={d.device_id} className="bg-card border border-border rounded-2xl p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-semibold text-foreground">{d.name}</div>
                  <div className="text-xs text-muted-foreground font-mono">{d.device_id}</div>
                </div>
                <Badge className={d.active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300' : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'}>{d.active ? 'Active' : 'Inactive'}</Badge>
              </div>
              <div className="mt-3 space-y-1.5 text-sm">
                <div className="flex items-center gap-2 text-muted-foreground"><Signal className="w-3.5 h-3.5" /> Assigned: <span className="text-foreground">{nameOf(d.assigned_to)}</span></div>
                <div className="flex items-center gap-2 text-muted-foreground"><Battery className="w-3.5 h-3.5" /> Battery: <span className="text-foreground">{d.battery}%</span></div>
                <div className="flex items-center gap-2 text-muted-foreground"><MapPin className="w-3.5 h-3.5" /> Last seen: <span className="text-foreground">Auckland CBD</span></div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add GPS device</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-2">
            <div><Label>Device name / label</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Van 1, Trailer B" className="mt-1.5" /></div>
            <div><Label>Assign to worker (optional)</Label>
              <select value={form.assigned_to} onChange={(e) => setForm({ ...form, assigned_to: e.target.value })} className="mt-1.5 w-full h-10 rounded-md border border-input bg-background px-3 text-sm">
                <option value="">Unassigned</option>
                {members.map((m) => <option key={m.member_id} value={m.member_id}>{m.name}</option>)}
              </select>
            </div>
            <Button onClick={add} className="w-full">Add device</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
