import React, { useEffect, useState, useCallback } from 'react';
import { KeyRound, Plus, Check, X, Loader2, Home, Building2, Landmark, Mail, MapPin } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../../components/ui/dialog';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';
import api from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import { extractError } from '../../lib/errors';

const APPROVER_ROLE_META = {
  landlord: { label: 'Landlord', icon: KeyRound, color: 'bg-orange-500' },
  property: { label: 'Property Manager', icon: Building2, color: 'bg-violet-500' },
  facilities: { label: 'Facilities Management', icon: Landmark, color: 'bg-slate-600' },
};

const APPROVER_ROLES = new Set(['landlord', 'property', 'facilities']);

const STATUS_META = {
  pending: { label: 'Pending approval', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300' },
  active: { label: 'Active', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300' },
  rejected: { label: 'Rejected', cls: 'bg-rose-100 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300' },
  archived: { label: 'Archived', cls: 'bg-muted text-muted-foreground' },
};

export default function Tenancies() {
  const { user } = useAuth();
  const isApprover = APPROVER_ROLES.has(user?.role);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showRequest, setShowRequest] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ approver_email: '', approver_role: 'landlord', label: '' });

  const load = useCallback(() => {
    setLoading(true);
    api.get('/tenancies/mine')
      .then((r) => setItems(r.data))
      .catch((err) => toast.error(extractError(err, 'Failed to load')))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post('/tenancies', form);
      toast.success('Request sent to your manager');
      setShowRequest(false);
      setForm({ approver_email: '', approver_role: 'landlord', label: '' });
      load();
    } catch (err) {
      toast.error(extractError(err, 'Failed to send'));
    } finally {
      setSaving(false);
    }
  };

  const action = async (id, verb) => {
    try {
      if (verb === 'archive') {
        await api.delete(`/tenancies/${id}`);
      } else {
        await api.post(`/tenancies/${id}/${verb}`);
      }
      toast.success('Done');
      load();
    } catch (err) {
      toast.error(extractError(err, 'Failed'));
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6" data-testid="tenancies-page">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            {isApprover ? 'Tenant Requests' : 'My Property Link'}
          </h1>
          <p className="text-muted-foreground mt-1">
            {isApprover
              ? 'Tenants who have linked with you. Approve to receive their maintenance requests.'
              : 'Link with your landlord or property manager so maintenance requests can be routed for approval.'}
          </p>
        </div>
        {!isApprover && (
          <Button data-testid="link-manager-btn" onClick={() => setShowRequest(true)}>
            <Plus className="w-4 h-4 mr-1.5" /> Link a manager
          </Button>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
      ) : items.length === 0 ? (
        <EmptyState isApprover={isApprover} onLink={() => setShowRequest(true)} />
      ) : (
        <div className="space-y-3">
          {items.map((t) => (
            <TenancyCard key={t.tenancy_id} t={t} isApprover={isApprover} onAction={action} />
          ))}
        </div>
      )}

      <Dialog open={showRequest} onOpenChange={setShowRequest}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Link with your manager</DialogTitle>
            <DialogDescription>Enter your landlord or property manager&apos;s email. They&apos;ll receive an approval request in-app.</DialogDescription>
          </DialogHeader>
          <form onSubmit={submit} className="space-y-4 mt-2">
            <div>
              <Label>Manager role</Label>
              <Select value={form.approver_role} onValueChange={(v) => setForm({ ...form, approver_role: v })}>
                <SelectTrigger data-testid="approver-role-select" className="mt-1.5"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="landlord">Landlord</SelectItem>
                  <SelectItem value="property">Property Manager</SelectItem>
                  <SelectItem value="facilities">Facilities Management</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Manager email</Label>
              <div className="relative mt-1.5">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  data-testid="approver-email-input"
                  type="email"
                  required
                  value={form.approver_email}
                  onChange={(e) => setForm({ ...form, approver_email: e.target.value })}
                  placeholder="landlord@example.com"
                  className="pl-9"
                />
              </div>
            </div>
            <div>
              <Label>Property label (optional)</Label>
              <div className="relative mt-1.5">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  data-testid="tenancy-label-input"
                  value={form.label}
                  onChange={(e) => setForm({ ...form, label: e.target.value })}
                  placeholder="e.g. 12 Grey Lynn Ave — Room 2"
                  className="pl-9"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowRequest(false)}>Cancel</Button>
              <Button data-testid="submit-tenancy-request" type="submit" disabled={saving}>
                {saving ? <><Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> Sending...</> : 'Send request'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function EmptyState({ isApprover, onLink }) {
  return (
    <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
      <Home className="w-10 h-10 mx-auto text-muted-foreground opacity-40 mb-3" />
      <div className="font-medium text-foreground">
        {isApprover ? 'No tenant requests yet' : 'You haven\'t linked a manager yet'}
      </div>
      <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
        {isApprover
          ? 'Once your tenants request to link with you, they\'ll appear here for approval.'
          : 'Link your landlord or property manager to route maintenance requests through them for approval and billing.'}
      </p>
      {!isApprover && (
        <Button onClick={onLink} className="mt-4"><Plus className="w-4 h-4 mr-1.5" /> Link a manager</Button>
      )}
    </div>
  );
}

function TenancyCard({ t, isApprover, onAction }) {
  const meta = APPROVER_ROLE_META[t.approver_role] || APPROVER_ROLE_META.landlord;
  const Icon = meta.icon;
  const status = STATUS_META[t.status] || STATUS_META.pending;
  const counterparty = isApprover ? t.tenant : t.approver;
  const counterpartyLine = counterparty
    ? `${counterparty.name || counterparty.email}${counterparty.email ? ` · ${counterparty.email}` : ''}`
    : t.approver_email;
  return (
    <div className="bg-card border border-border rounded-2xl p-4 flex items-center gap-4" data-testid={`tenancy-card-${t.tenancy_id}`}>
      <div className={`w-11 h-11 rounded-xl ${meta.color} flex items-center justify-center text-white shrink-0`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <div className="font-semibold text-foreground truncate">{t.label || meta.label}</div>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${status.cls}`}>{status.label}</span>
        </div>
        <div className="text-xs text-muted-foreground mt-0.5 truncate">{counterpartyLine}</div>
      </div>
      <div className="flex items-center gap-2">
        {isApprover && t.status === 'pending' && (
          <>
            <Button data-testid={`approve-tenancy-${t.tenancy_id}`} size="sm" onClick={() => onAction(t.tenancy_id, 'approve')} className="bg-emerald-600 hover:bg-emerald-700">
              <Check className="w-4 h-4 mr-1" /> Approve
            </Button>
            <Button data-testid={`reject-tenancy-${t.tenancy_id}`} size="sm" variant="outline" onClick={() => onAction(t.tenancy_id, 'reject')}>
              <X className="w-4 h-4 mr-1" /> Reject
            </Button>
          </>
        )}
        {t.status !== 'archived' && (
          <Button data-testid={`archive-tenancy-${t.tenancy_id}`} size="sm" variant="ghost" onClick={() => onAction(t.tenancy_id, 'archive')}>Archive</Button>
        )}
      </div>
    </div>
  );
}
