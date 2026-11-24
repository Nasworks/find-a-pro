import React, { useCallback, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { FileText, Check, X, Loader2, ExternalLink } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { mediaSrc } from '../../components/MediaUploader';
import { useAuth } from '../../context/AuthContext';
import api from '../../lib/api';
import { toast } from 'sonner';

const KIND = { qualification: 'Qualification', certification: 'Licence / certification', police_check: 'Police check' };

export default function ReviewDocuments() {
  const { user } = useAuth();
  const [status, setStatus] = useState('pending');
  const [docs, setDocs] = useState(null);
  const [notes, setNotes] = useState({});
  const [busy, setBusy] = useState(null);

  const load = useCallback(() => {
    api.get('/review/documents', { params: { status } }).then((r) => setDocs(r.data)).catch(() => setDocs([]));
  }, [status]);
  useEffect(() => { if (user?.is_reviewer) load(); }, [load, user?.is_reviewer]);

  if (!user?.is_reviewer) return <Navigate to="/" replace />;

  const decide = async (d, decision) => {
    setBusy(d.doc_id);
    try {
      await api.post(`/review/documents/${d.doc_id}`, { decision, note: notes[d.doc_id] || '' });
      toast.success(decision === 'approve' ? 'Approved — tick added to the provider profile' : 'Sent back to the provider');
      load();
    } catch (err) { toast.error(err?.response?.data?.detail || 'Could not save'); } finally { setBusy(null); }
  };

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 space-y-5" data-testid="review-documents">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Review provider documents</h1>
        <p className="text-sm text-muted-foreground">Approving a qualification, licence or police check adds a verified tick to the provider's profile.</p>
      </div>
      <div className="inline-flex rounded-xl bg-muted p-1">
        {['pending', 'approved', 'rejected'].map((s) => (
          <button key={s} type="button" onClick={() => setStatus(s)} data-testid={`review-tab-${s}`}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium capitalize ${status === s ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground'}`}>{s}</button>
        ))}
      </div>
      {docs === null ? <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /> : docs.length === 0 ? (
        <div className="text-sm text-muted-foreground text-center py-10">Nothing here</div>
      ) : docs.map((d) => (
        <div key={d.doc_id} className="bg-card border border-border rounded-xl p-4" data-testid={`review-doc-${d.doc_id}`}>
          <div className="flex items-start gap-3">
            <FileText className="w-5 h-5 text-muted-foreground mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-foreground">{d.title}</span>
                <Badge variant="outline">{KIND[d.kind]}</Badge>
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">{d.provider_name}{d.issuer ? ` · ${d.issuer}` : ''}{d.reference ? ` · #${d.reference}` : ''}{d.expiry ? ` · ${d.expiry}` : ''}</div>
              <a href={mediaSrc(d.file_url)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-primary hover:underline mt-1" data-testid={`review-open-${d.doc_id}`}>Open document <ExternalLink className="w-3 h-3" /></a>
              {d.review_note && <div className="text-xs text-muted-foreground mt-1">Note: {d.review_note}</div>}
            </div>
          </div>
          {d.status === 'pending' && (
            <div className="flex flex-col sm:flex-row gap-2 mt-3">
              <Input placeholder="Reason (required to send back)" value={notes[d.doc_id] || ''} onChange={(e) => setNotes({ ...notes, [d.doc_id]: e.target.value })} className="flex-1" data-testid={`review-note-${d.doc_id}`} />
              <Button variant="outline" onClick={() => decide(d, 'reject')} disabled={busy === d.doc_id} data-testid={`review-reject-${d.doc_id}`}><X className="w-4 h-4 mr-1" /> Send back</Button>
              <Button onClick={() => decide(d, 'approve')} disabled={busy === d.doc_id} data-testid={`review-approve-${d.doc_id}`}><Check className="w-4 h-4 mr-1" /> Approve</Button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
