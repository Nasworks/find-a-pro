import React, { useEffect, useState } from 'react';
import { Plus, FileText, X, Send, Edit, Download, Trash2 } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import api from '../../lib/api';
import { toast } from 'sonner';

export default function Quotations() {
  const [quotes, setQuotes] = useState([]);
  const [tab, setTab] = useState('all');
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);

  const load = async () => {
    const r = await api.get('/quotations/mine');
    setQuotes(r.data);
  };
  useEffect(() => { load(); }, []);

  const filtered = tab === 'all' ? quotes : quotes.filter((q) => q.status === tab);
  const counts = { all: quotes.length, draft: quotes.filter((q) => q.status === 'draft').length, sent: quotes.filter((q) => q.status === 'sent').length, accepted: quotes.filter((q) => q.status === 'accepted').length };

  const statusColors = {
    draft: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    sent: 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300',
    accepted: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300',
    rejected: 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300',
    expired: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
  };

  const send = async (q) => {
    await api.patch(`/quotations/${q.quote_id}`, { status: 'sent' });
    toast.success('Quote sent to client');
    load();
  };
  const remove = async (q) => {
    await api.delete(`/quotations/${q.quote_id}`);
    toast.success('Deleted');
    load();
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Quotations</h1>
          <p className="text-sm text-muted-foreground">Create detailed quotes for larger jobs</p>
        </div>
        <Button onClick={() => { setEditing(null); setOpen(true); }}><Plus className="w-4 h-4 mr-1" /> New Quote</Button>
      </div>

      <div className="flex gap-2 mb-6 border-b border-border">
        {[
          { k: 'all', l: `All (${counts.all})` },
          { k: 'draft', l: `Draft (${counts.draft})` },
          { k: 'sent', l: `Sent (${counts.sent})` },
          { k: 'accepted', l: `Accepted (${counts.accepted})` },
        ].map((t) => (
          <button key={t.k} onClick={() => setTab(t.k)} className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${tab === t.k ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>{t.l}</button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
          <FileText className="w-10 h-10 mx-auto text-muted-foreground mb-3 opacity-40" />
          <div className="font-medium text-foreground">No quotes yet</div>
          <p className="text-sm text-muted-foreground mt-1">Create quotes to formalize offers for larger jobs.</p>
          <Button className="mt-4" onClick={() => setOpen(true)}>Create your first quote</Button>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((q) => (
            <div key={q.quote_id} className="bg-card border border-border rounded-2xl p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <div className="font-semibold text-foreground">{q.title}</div>
                    <Badge className={statusColors[q.status]}>{q.status}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">To: {q.client_name} · Created {new Date(q.created_at).toLocaleDateString()} {q.valid_until && `· Valid until ${q.valid_until}`}</div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-primary">${q.total.toFixed(2)}</div>
                  <div className="text-[10px] text-muted-foreground">Inc GST</div>
                </div>
              </div>
              {q.line_items?.length > 0 && (
                <div className="mt-3 text-sm text-muted-foreground">{q.line_items.length} line item{q.line_items.length !== 1 ? 's' : ''} · Subtotal ${q.subtotal.toFixed(2)} · GST ${q.tax.toFixed(2)}</div>
              )}
              <div className="flex gap-2 mt-4 flex-wrap">
                <Button size="sm" variant="outline" onClick={() => { setEditing(q); setOpen(true); }}><Edit className="w-3.5 h-3.5 mr-1" /> Edit</Button>
                {q.status === 'draft' && <Button size="sm" onClick={() => send(q)}><Send className="w-3.5 h-3.5 mr-1" /> Send</Button>}
                <Button size="sm" variant="outline"><Download className="w-3.5 h-3.5 mr-1" /> PDF</Button>
                <Button size="sm" variant="outline" className="text-destructive hover:text-destructive" onClick={() => remove(q)}><Trash2 className="w-3.5 h-3.5" /></Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {open && <QuoteDialog editing={editing} onClose={() => setOpen(false)} onSuccess={() => { setOpen(false); load(); }} />}
    </div>
  );
}

function QuoteDialog({ editing, onClose, onSuccess }) {
  const [form, setForm] = useState({
    title: editing?.title || '',
    client_name: editing?.client_name || '',
    description: editing?.description || '',
    line_items: editing?.line_items?.length ? editing.line_items : [{ label: '', qty: 1, unit_price: 0 }],
    valid_until: editing?.valid_until || '',
  });
  const [saving, setSaving] = useState(false);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const updateItem = (i, k, v) => setForm((f) => ({ ...f, line_items: f.line_items.map((it, idx) => idx === i ? { ...it, [k]: k === 'label' ? v : Number(v) || 0 } : it) }));
  const addItem = () => setForm((f) => ({ ...f, line_items: [...f.line_items, { label: '', qty: 1, unit_price: 0 }] }));
  const removeItem = (i) => setForm((f) => ({ ...f, line_items: f.line_items.filter((_, idx) => idx !== i) }));

  const subtotal = form.line_items.reduce((s, i) => s + (i.qty || 0) * (i.unit_price || 0), 0);
  const gst = subtotal * 0.15;
  const total = subtotal + gst;

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editing) {
        await api.patch(`/quotations/${editing.quote_id}`, { ...form, line_items: form.line_items.filter((i) => i.label) });
      } else {
        await api.post('/quotations', { ...form, line_items: form.line_items.filter((i) => i.label) });
      }
      toast.success(editing ? 'Quote updated' : 'Quote created');
      onSuccess();
    } catch { toast.error('Failed'); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto scrollbar-thin">
        <DialogHeader><DialogTitle>{editing ? 'Edit quote' : 'New quote'}</DialogTitle></DialogHeader>
        <form onSubmit={submit} className="space-y-4 mt-2">
          <div className="grid grid-cols-2 gap-3">
            <div><Label>Title</Label><Input value={form.title} onChange={(e) => update('title', e.target.value)} className="mt-1.5" required /></div>
            <div><Label>Client name</Label><Input value={form.client_name} onChange={(e) => update('client_name', e.target.value)} className="mt-1.5" required /></div>
          </div>
          <div><Label>Description</Label><Textarea rows={2} value={form.description} onChange={(e) => update('description', e.target.value)} className="mt-1.5" /></div>
          <div>
            <div className="flex items-center justify-between mb-2"><Label>Line items</Label><Button type="button" size="sm" variant="outline" onClick={addItem}><Plus className="w-3 h-3 mr-1" /> Add</Button></div>
            <div className="space-y-2">
              {form.line_items.map((it, i) => (
                <div key={i} className="grid grid-cols-[1fr_60px_100px_100px_28px] gap-2 items-center">
                  <Input value={it.label} onChange={(e) => updateItem(i, 'label', e.target.value)} placeholder="Description" />
                  <Input type="number" value={it.qty} onChange={(e) => updateItem(i, 'qty', e.target.value)} placeholder="Qty" />
                  <Input type="number" value={it.unit_price} onChange={(e) => updateItem(i, 'unit_price', e.target.value)} placeholder="Unit $" />
                  <div className="text-sm font-medium text-right pr-2">${((it.qty || 0) * (it.unit_price || 0)).toFixed(2)}</div>
                  <button type="button" onClick={() => removeItem(i)} className="text-muted-foreground hover:text-destructive p-1"><X className="w-3.5 h-3.5" /></button>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-muted/40 rounded-lg p-3 space-y-1 text-sm">
            <div className="flex justify-between"><span className="text-muted-foreground">Subtotal</span><span>${subtotal.toFixed(2)}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">GST (15%)</span><span>${gst.toFixed(2)}</span></div>
            <div className="flex justify-between font-bold text-foreground"><span>Total</span><span>${total.toFixed(2)}</span></div>
          </div>
          <div><Label>Valid until</Label><Input type="date" value={form.valid_until} onChange={(e) => update('valid_until', e.target.value)} className="mt-1.5" /></div>
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving} className="flex-1">{saving ? 'Saving...' : 'Save'}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
