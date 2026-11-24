import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ShieldCheck, Upload, FileText, Trash2, Loader2, GraduationCap, Award, ArrowRight, Clock, XCircle, BadgeCheck } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import CredentialTicks from '../../components/CredentialTicks';
import { uploadFile, mediaSrc } from '../../components/MediaUploader';
import { useAuth } from '../../context/AuthContext';
import api from '../../lib/api';
import { toast } from 'sonner';

const KINDS = [
  { v: 'qualification', l: 'Qualification', d: 'Trade certificate, apprenticeship, degree', icon: GraduationCap, ph: 'e.g. NZ Certificate in Plumbing (Level 4)' },
  { v: 'certification', l: 'Licence / certification', d: 'PGDB, EWRB, LBP, Site Safe, gas cert', icon: Award, ph: 'e.g. PGDB Certifying Plumber licence' },
  { v: 'police_check', l: 'Police check', d: 'NZ Police vetting or MoJ criminal record check', icon: ShieldCheck, ph: 'e.g. Ministry of Justice criminal record check' },
];
const STATUS = {
  pending: { l: 'Under review', icon: Clock, cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' },
  approved: { l: 'Verified', icon: BadgeCheck, cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' },
  rejected: { l: 'Needs attention', icon: XCircle, cls: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300' },
};
const ACCEPT = 'application/pdf,image/*';

export default function Verification() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const welcome = params.get('welcome') === '1';
  const [docs, setDocs] = useState([]);
  const [creds, setCreds] = useState(null);
  const [form, setForm] = useState({ kind: 'qualification', title: '', issuer: '', reference: '', expiry: '' });
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);

  const load = useCallback(() => {
    api.get('/providers/me/documents').then((r) => setDocs(r.data || [])).catch(() => setDocs([]));
    if (user?.user_id) api.get(`/providers/${user.user_id}/credentials`).then((r) => setCreds(r.data)).catch(() => {});
  }, [user?.user_id]);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    if (!form.title.trim()) { toast.error('Give the document a name'); return; }
    if (!file) { toast.error('Choose a PDF or photo of the document'); return; }
    setSaving(true); setProgress(1);
    try {
      const up = await uploadFile(file, setProgress);
      await api.post('/providers/me/documents', { ...form, file_url: up.url, file_name: up.name });
      toast.success('Uploaded — we\'ll review it and add the tick to your profile');
      setForm({ kind: form.kind, title: '', issuer: '', reference: '', expiry: '' });
      setFile(null);
      if (fileRef.current) fileRef.current.value = '';
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Upload failed');
    } finally { setSaving(false); setProgress(0); }
  };

  const remove = async (d) => {
    if (!window.confirm(`Remove ${d.title}?`)) return;
    try { await api.delete(`/providers/me/documents/${d.doc_id}`); load(); } catch { toast.error('Could not remove'); }
  };

  const kindMeta = KINDS.find((k) => k.v === form.kind);

  return (
    <div className="max-w-3xl mx-auto p-4 sm:p-6 space-y-6" data-testid="verification-page">
      <div>
        {welcome && <div className="text-xs font-semibold uppercase tracking-wider text-primary">Step 2 of 3 · optional</div>}
        <h1 className="text-2xl sm:text-3xl font-bold text-foreground mt-1">Qualifications &amp; police check</h1>
        <p className="text-sm text-muted-foreground mt-1">Upload your documents. Once our team reviews them, a verified tick appears on your profile so clients can trust you.</p>
        {creds && <CredentialTicks data={creds} showPending className="mt-3" />}
      </div>

      <div className="bg-card border border-border rounded-2xl p-5 space-y-4" data-testid="doc-upload-form">
        <div className="grid sm:grid-cols-3 gap-2">
          {KINDS.map(({ v, l, d, icon: Icon }) => (
            <button key={v} type="button" data-testid={`doc-kind-${v}`} onClick={() => setForm({ ...form, kind: v })}
              className={`p-3 rounded-xl border-2 text-left transition-colors ${form.kind === v ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}>
              <Icon className={`w-5 h-5 mb-1 ${form.kind === v ? 'text-primary' : 'text-muted-foreground'}`} />
              <div className="text-sm font-semibold text-foreground">{l}</div>
              <div className="text-xs text-muted-foreground">{d}</div>
            </button>
          ))}
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          <div className="sm:col-span-2">
            <Label>Document name</Label>
            <Input data-testid="doc-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder={kindMeta.ph} className="mt-1.5" maxLength={120} />
          </div>
          <div>
            <Label>Issued by <span className="text-muted-foreground font-normal">(optional)</span></Label>
            <Input value={form.issuer} onChange={(e) => setForm({ ...form, issuer: e.target.value })} placeholder={form.kind === 'police_check' ? 'NZ Police / Ministry of Justice' : 'e.g. PGDB'} className="mt-1.5" />
          </div>
          <div>
            <Label>{form.kind === 'police_check' ? 'Date issued / expiry' : 'Expiry date'} <span className="text-muted-foreground font-normal">(optional)</span></Label>
            <Input type="date" value={form.expiry} onChange={(e) => setForm({ ...form, expiry: e.target.value })} className="mt-1.5" />
          </div>
          <div className="sm:col-span-2">
            <Label>Licence / reference number <span className="text-muted-foreground font-normal">(optional)</span></Label>
            <Input value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} className="mt-1.5" maxLength={80} />
          </div>
        </div>
        <div>
          <input ref={fileRef} type="file" accept={ACCEPT} className="hidden" data-testid="doc-file-input" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <button type="button" onClick={() => fileRef.current?.click()} data-testid="doc-file-pick"
            className="w-full flex items-center justify-center gap-2 p-4 rounded-xl border-2 border-dashed border-border hover:border-primary/40 text-sm text-muted-foreground">
            <Upload className="w-4 h-4" /> {file ? file.name : 'Choose a PDF or photo of the document'}
          </button>
          {progress > 0 && <div className="h-1.5 rounded-full bg-muted mt-2 overflow-hidden"><div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} /></div>}
        </div>
        <Button onClick={submit} disabled={saving} className="w-full" data-testid="doc-submit">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Upload className="w-4 h-4 mr-2" /> Upload for review</>}
        </Button>
      </div>

      <div className="space-y-2" data-testid="doc-list">
        {docs.map((d) => {
          const st = STATUS[d.status] || STATUS.pending;
          const SI = st.icon;
          return (
            <div key={d.doc_id} className="flex items-start gap-3 bg-card border border-border rounded-xl p-4" data-testid={`doc-row-${d.doc_id}`}>
              <FileText className="w-5 h-5 text-muted-foreground mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <a href={mediaSrc(d.file_url)} target="_blank" rel="noreferrer" className="font-medium text-foreground hover:text-primary truncate">{d.title}</a>
                  <Badge className={`${st.cls} border-0 gap-1`} data-testid={`doc-status-${d.doc_id}`}><SI className="w-3 h-3" /> {st.l}</Badge>
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">{KINDS.find((k) => k.v === d.kind)?.l}{d.issuer ? ` · ${d.issuer}` : ''}{d.expiry ? ` · ${d.expiry}` : ''}</div>
                {d.status === 'rejected' && d.review_note && <div className="text-xs text-rose-600 mt-1">Reviewer: {d.review_note}</div>}
              </div>
              <button type="button" onClick={() => remove(d)} className="p-2 rounded-lg text-muted-foreground hover:text-destructive hover:bg-accent" aria-label="Remove"><Trash2 className="w-4 h-4" /></button>
            </div>
          );
        })}
        {docs.length === 0 && <div className="text-sm text-muted-foreground text-center py-6">No documents uploaded yet</div>}
      </div>

      {welcome && (
        <div className="flex gap-3">
          <Button variant="outline" className="flex-1" onClick={() => navigate('/provider/onboarding')} data-testid="doc-skip">Skip for now</Button>
          <Button className="flex-1" onClick={() => navigate('/provider/onboarding')} data-testid="doc-continue">Continue to your services <ArrowRight className="w-4 h-4 ml-1" /></Button>
        </div>
      )}
    </div>
  );
}
