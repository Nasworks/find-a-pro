import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Camera, ImagePlus, Loader2, Sparkles, Trash2, Receipt as ReceiptIcon, Package, Wrench, Truck, Users, Car, Fuel, MoreHorizontal } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { uploadFile, mediaSrc } from '../../components/MediaUploader';
import api from '../../lib/api';
import { toast } from 'sonner';

export const COST_TYPES = [
  { v: 'materials', l: 'Materials', icon: Package },
  { v: 'equipment_purchase', l: 'Equipment purchase', icon: Wrench },
  { v: 'equipment_hire', l: 'Equipment hire', icon: Truck },
  { v: 'third_party', l: 'Third-party service', icon: Users },
  { v: 'travel', l: 'Travel', icon: Car },
  { v: 'fuel', l: 'Fuel', icon: Fuel },
  { v: 'other', l: 'Other', icon: MoreHorizontal },
];
const label = (v) => COST_TYPES.find((c) => c.v === v)?.l || v;
const money = (n) => `$${Number(n || 0).toFixed(2)}`;
const EMPTY = { file_url: null, cost_type: 'materials', supplier: '', date: '', total: '', gst: '', items: [], notes: '', job_id: '' };

export default function Receipts() {
  const [data, setData] = useState({ receipts: [], totals: {}, grand_total: 0 });
  const [jobs, setJobs] = useState([]);
  const [form, setForm] = useState(null);
  const [preview, setPreview] = useState(null);
  const [stage, setStage] = useState('');
  const [saving, setSaving] = useState(false);
  const cameraRef = useRef(null);
  const galleryRef = useRef(null);

  const load = useCallback(() => {
    api.get('/receipts').then((r) => setData(r.data)).catch(() => {});
  }, []);
  useEffect(() => {
    load();
    api.get('/matches/mine').then((r) => setJobs((r.data || []).filter((m) => m.match_status === 'awarded').map((m) => m.job))).catch(() => {});
  }, [load]);

  const onFile = async (file) => {
    if (!file) return;
    setPreview(URL.createObjectURL(file));
    setForm({ ...EMPTY });
    try {
      setStage('Uploading…');
      const up = await uploadFile(file);
      setForm((f) => ({ ...f, file_url: up.url }));
      if (!file.type.startsWith('image/')) { setStage(''); return; }
      setStage('Reading receipt…');
      const r = await api.post('/receipts/scan', { file_url: up.url });
      const d = r.data || {};
      if (d.is_receipt === false) toast.info("That doesn't look like a receipt — check the details below");
      setForm((f) => ({
        ...f, supplier: d.supplier || '', date: d.date || '', total: d.total ?? '', gst: d.gst ?? '',
        items: d.items || [], cost_type: d.suggested_cost_type || f.cost_type,
      }));
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not read the receipt — enter it manually');
    } finally { setStage(''); }
  };

  const save = async () => {
    if (!(Number(form.total) > 0)) { toast.error('Enter the receipt total'); return; }
    setSaving(true);
    try {
      await api.post('/receipts', {
        ...form, total: Number(form.total), gst: form.gst === '' ? null : Number(form.gst),
        job_id: form.job_id || null, date: form.date || null,
      });
      toast.success('Receipt saved');
      setForm(null); setPreview(null);
      load();
    } catch (err) { toast.error(err?.response?.data?.detail || 'Could not save'); } finally { setSaving(false); }
  };

  const remove = async (r) => {
    if (!window.confirm('Delete this receipt?')) return;
    await api.delete(`/receipts/${r.receipt_id}`).catch(() => toast.error('Could not delete'));
    load();
  };

  return (
    <div className="max-w-3xl mx-auto p-4 sm:p-6 space-y-6" data-testid="receipts-page">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-foreground">Receipts</h1>
        <p className="text-sm text-muted-foreground mt-1">Snap a receipt and AI fills in the supplier, date and total. Tag what kind of cost it is and attach it to a job.</p>
      </div>

      <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" data-testid="receipt-camera-input" onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ''; }} />
      <input ref={galleryRef} type="file" accept="image/*,application/pdf" className="hidden" data-testid="receipt-file-input" onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ''; }} />

      {!form && (
        <div className="grid grid-cols-2 gap-3">
          <button type="button" onClick={() => cameraRef.current?.click()} data-testid="receipt-take-photo" className="p-6 rounded-2xl border-2 border-dashed border-primary/40 bg-primary/5 hover:border-primary text-center">
            <Camera className="w-7 h-7 text-primary mx-auto" /><div className="font-semibold text-foreground mt-2">Take photo</div><div className="text-xs text-muted-foreground">Use your camera</div>
          </button>
          <button type="button" onClick={() => galleryRef.current?.click()} data-testid="receipt-upload" className="p-6 rounded-2xl border-2 border-dashed border-border hover:border-primary/40 text-center">
            <ImagePlus className="w-7 h-7 text-muted-foreground mx-auto" /><div className="font-semibold text-foreground mt-2">Upload</div><div className="text-xs text-muted-foreground">Photo or PDF</div>
          </button>
        </div>
      )}

      {form && (
        <div className="bg-card border border-border rounded-2xl p-5 space-y-4" data-testid="receipt-form">
          <div className="flex gap-4">
            {preview && <img src={preview} alt="Receipt" className="w-24 h-32 object-cover rounded-lg border border-border shrink-0" />}
            <div className="flex-1 min-w-0">
              {stage ? (
                <div className="flex items-center gap-2 text-sm text-primary" data-testid="receipt-stage"><Loader2 className="w-4 h-4 animate-spin" /> {stage}</div>
              ) : (
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground"><Sparkles className="w-4 h-4 text-primary" /> Check the details, then save</div>
              )}
              <div className="grid grid-cols-2 gap-2 mt-3">
                <div className="col-span-2"><Label>Supplier</Label><Input data-testid="receipt-supplier" value={form.supplier} onChange={(e) => setForm({ ...form, supplier: e.target.value })} className="mt-1" /></div>
                <div><Label>Total (NZD)</Label><Input data-testid="receipt-total" type="number" step="0.01" value={form.total} onChange={(e) => setForm({ ...form, total: e.target.value })} className="mt-1" /></div>
                <div><Label>GST</Label><Input type="number" step="0.01" value={form.gst} onChange={(e) => setForm({ ...form, gst: e.target.value })} className="mt-1" /></div>
                <div className="col-span-2"><Label>Date</Label><Input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} className="mt-1" /></div>
              </div>
            </div>
          </div>
          <div>
            <Label>Cost type</Label>
            <div className="flex flex-wrap gap-2 mt-1.5">
              {COST_TYPES.map(({ v, l, icon: Icon }) => (
                <button key={v} type="button" data-testid={`receipt-type-${v}`} aria-pressed={form.cost_type === v} onClick={() => setForm({ ...form, cost_type: v })}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm border transition-colors ${form.cost_type === v ? 'bg-primary text-primary-foreground border-primary' : 'border-border text-muted-foreground hover:border-primary/40'}`}>
                  <Icon className="w-3.5 h-3.5" /> {l}
                </button>
              ))}
            </div>
          </div>
          <div>
            <Label>Job <span className="text-muted-foreground font-normal">(optional)</span></Label>
            <select data-testid="receipt-job" value={form.job_id} onChange={(e) => setForm({ ...form, job_id: e.target.value })} className="mt-1.5 w-full h-10 rounded-md border border-input bg-transparent px-3 text-sm">
              <option value="">Not linked to a job</option>
              {jobs.map((j) => <option key={j.job_id} value={j.job_id}>{j.title}</option>)}
            </select>
          </div>
          {form.items.length > 0 && (
            <div className="text-xs text-muted-foreground space-y-0.5 border-t border-border pt-3">
              {form.items.map((it, i) => <div key={i} className="flex justify-between"><span className="truncate pr-3">{it.description}</span><span className="tabular-nums">{money(it.amount)}</span></div>)}
            </div>
          )}
          <div><Label>Notes</Label><Textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} className="mt-1" placeholder="e.g. approved by client in chat" /></div>
          <div className="flex gap-2">
            <Button variant="outline" className="flex-1" onClick={() => { setForm(null); setPreview(null); }}>Cancel</Button>
            <Button className="flex-1" onClick={save} disabled={saving || !!stage} data-testid="receipt-save">{saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save receipt'}</Button>
          </div>
        </div>
      )}

      {Object.keys(data.totals).length > 0 && (
        <div className="flex flex-wrap gap-2" data-testid="receipt-totals">
          {Object.entries(data.totals).map(([k, v]) => <span key={k} className="rounded-full bg-muted px-3 py-1 text-xs text-foreground">{label(k)} · {money(v)}</span>)}
          <span className="rounded-full bg-primary/10 text-primary px-3 py-1 text-xs font-semibold">Total · {money(data.grand_total)}</span>
        </div>
      )}

      <div className="space-y-2" data-testid="receipt-list">
        {data.receipts.map((r) => (
          <div key={r.receipt_id} className="flex items-center gap-3 bg-card border border-border rounded-xl p-3" data-testid={`receipt-row-${r.receipt_id}`}>
            <ReceiptIcon className="w-5 h-5 text-muted-foreground shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="font-medium text-foreground truncate">{r.supplier || 'Receipt'} <span className="text-xs text-muted-foreground font-normal">· {label(r.cost_type)}</span></div>
              <div className="text-xs text-muted-foreground truncate">{r.date || ''}{r.job_title ? ` · ${r.job_title}` : ''}</div>
            </div>
            <div className="font-semibold tabular-nums text-foreground">{money(r.total)}</div>
            {r.file_url && <a href={mediaSrc(r.file_url)} target="_blank" rel="noreferrer" className="text-xs text-primary hover:underline">View</a>}
            <button type="button" onClick={() => remove(r)} className="p-1.5 text-muted-foreground hover:text-destructive" aria-label="Delete"><Trash2 className="w-4 h-4" /></button>
          </div>
        ))}
        {data.receipts.length === 0 && !form && <div className="text-sm text-muted-foreground text-center py-8">No receipts yet</div>}
      </div>
    </div>
  );
}
