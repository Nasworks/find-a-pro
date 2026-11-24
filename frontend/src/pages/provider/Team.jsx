import React, { useEffect, useState } from 'react';
import { Plus, Users, Phone, Mail, Trash2, KeyRound, Send, MessagesSquare } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import InviteDialog from '../../components/team/InviteDialog';
import SendJobDialog from '../../components/team/SendJobDialog';
import TeamAssignments from '../../components/team/TeamAssignments';
import TeamSettingsCard from '../../components/team/TeamSettingsCard';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import api from '../../lib/api';
import { toast } from 'sonner';

const statusColors = {
  available: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300',
  on_job: 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300',
  off_duty: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
};

export default function Team() {
  const [members, setMembers] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: '', role: 'Worker', phone: '', email: '', hourly_rate: 45, skills: '' });

  const [assignments, setAssignments] = useState([]);
  const [inviting, setInviting] = useState(null);
  const [sendTo, setSendTo] = useState(null);

  const load = async () => {
    const [r, a] = await Promise.all([api.get('/team'), api.get('/team/assignments')]);
    setMembers(r.data);
    setAssignments(a.data);
  };
  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!form.name) return;
    await api.post('/team', { ...form, hourly_rate: Number(form.hourly_rate), skills: form.skills.split(',').map((s) => s.trim()).filter(Boolean) });
    toast.success('Team member added');
    setOpen(false);
    setForm({ name: '', role: 'Worker', phone: '', email: '', hourly_rate: 45, skills: '' });
    load();
  };

  const remove = async (id) => {
    await api.delete(`/team/${id}`);
    toast.success('Removed');
    load();
  };

  const setStatus = async (id, status) => {
    await api.patch(`/team/${id}`, { status });
    load();
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Team</h1>
          <p className="text-sm text-muted-foreground">Give employees their own login, send them jobs and see their timesheets</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild><Link to="/team/board" data-testid="team-board-link"><MessagesSquare className="w-4 h-4 mr-1" /> Team board</Link></Button>
          <Button onClick={() => setOpen(true)} data-testid="add-worker-btn"><Plus className="w-4 h-4 mr-1" /> Add Worker</Button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Total workers" value={members.length} />
        <StatCard label="Available" value={members.filter((m) => m.status === 'available').length} />
        <StatCard label="On job" value={members.filter((m) => m.status === 'on_job').length} />
        <StatCard label="Off duty" value={members.filter((m) => m.status === 'off_duty').length} />
      </div>

      <Tabs defaultValue="members">
        <TabsList className="mb-4">
          <TabsTrigger value="members" data-testid="team-tab-members">Members</TabsTrigger>
          <TabsTrigger value="jobs" data-testid="team-tab-jobs">Jobs sent ({assignments.filter((a) => a.status !== 'cancelled').length})</TabsTrigger>
          <TabsTrigger value="settings" data-testid="team-tab-settings">Timesheet settings</TabsTrigger>
        </TabsList>
        <TabsContent value="jobs"><TeamAssignments items={assignments} onChange={load} /></TabsContent>
        <TabsContent value="settings"><TeamSettingsCard /></TabsContent>
        <TabsContent value="members">
      {members.length === 0 ? (
        <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
          <Users className="w-10 h-10 mx-auto text-muted-foreground mb-3 opacity-40" />
          <div className="font-medium text-foreground">No team members yet</div>
          <p className="text-sm text-muted-foreground mt-1">Add workers to dispatch them to jobs, track locations, and manage payroll.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {members.map((m) => (
            <div key={m.member_id} className="bg-card border border-border rounded-2xl p-4" data-testid={`team-member-${m.member_id}`}>
              <div className="flex items-start gap-3">
                <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary to-blue-600 text-white text-xs font-bold flex items-center justify-center">
                  {m.name.split(' ').map((s) => s[0]).slice(0, 2).join('')}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <div className="font-semibold text-foreground truncate">{m.name}</div>
                    <Badge className={statusColors[m.status]}>{m.status.replace('_', ' ')}</Badge>
                    <LoginBadge m={m} />
                  </div>
                  <div className="text-xs text-muted-foreground">{m.role} · ${m.hourly_rate}/hr</div>
                  {m.skills?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {m.skills.map((s) => <span key={s} className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary">{s}</span>)}
                    </div>
                  )}
                  <div className="flex gap-3 mt-2 text-xs text-muted-foreground">
                    {m.phone && <span className="inline-flex items-center gap-1"><Phone className="w-3 h-3" /> {m.phone}</span>}
                    {m.email && <span className="inline-flex items-center gap-1"><Mail className="w-3 h-3" /> {m.email}</span>}
                  </div>
                </div>
                <button onClick={() => remove(m.member_id)} aria-label="Remove member" data-testid="team-member-remove" className="p-1 text-muted-foreground hover:text-destructive"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
              <div className="flex flex-wrap gap-2 mt-3">
                <Button size="sm" onClick={() => setSendTo(m)} data-testid="team-member-send-job"><Send className="w-3.5 h-3.5 mr-1" /> Send job</Button>
                {!m.linked_user_id && <Button size="sm" variant="outline" onClick={() => setInviting(m)} data-testid="team-member-invite"><KeyRound className="w-3.5 h-3.5 mr-1" /> {m.invite_status === 'invited' ? 'Resend invite' : 'Give login'}</Button>}
              </div>
              <div className="flex gap-1 mt-3">
                {['available', 'on_job', 'off_duty'].map((s) => (
                  <button key={s} onClick={() => setStatus(m.member_id, s)} className={`px-2 py-1 rounded text-[10px] font-medium capitalize transition-colors ${m.status === s ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>{s.replace('_', ' ')}</button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
        </TabsContent>
      </Tabs>

      <InviteDialog member={inviting} onClose={() => setInviting(null)} onDone={load} />
      <SendJobDialog member={sendTo} onClose={() => setSendTo(null)} onDone={() => { setSendTo(null); load(); }} />

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add team member</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-2">
            <div><Label>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1.5" data-testid="add-member-name" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Role</Label><Input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} placeholder="e.g. Sparky, Plumber" className="mt-1.5" /></div>
              <div><Label>Hourly rate</Label><Input type="number" value={form.hourly_rate} onChange={(e) => setForm({ ...form, hourly_rate: e.target.value })} className="mt-1.5" /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Phone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="mt-1.5" /></div>
              <div><Label>Email</Label><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="mt-1.5" data-testid="add-member-email" /></div>
            </div>
            <div><Label>Skills (comma separated)</Label><Input value={form.skills} onChange={(e) => setForm({ ...form, skills: e.target.value })} placeholder="e.g. Wiring, Solar, EV chargers" className="mt-1.5" /></div>
            <Button onClick={add} className="w-full" data-testid="add-member-submit">Add member</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function LoginBadge({ m }) {
  if (m.linked_user_id) return <Badge className="bg-emerald-600 text-white" data-testid="login-active-badge">has login</Badge>;
  if (m.invite_status === 'invited') return <Badge variant="outline" data-testid="login-invited-badge">invited</Badge>;
  return null;
}

function StatCard({ label, value }) {
  return (
    <div className="bg-card border border-border rounded-2xl p-4">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-2xl font-bold text-foreground mt-1">{value}</div>
    </div>
  );
}
