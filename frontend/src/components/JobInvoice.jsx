import React, { useEffect, useState, useCallback } from 'react';
import { Receipt, Loader2, Send, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from './ui/button';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';
import PayInvoiceButton from './PayInvoiceButton';

const money = (n) => `$${Number(n || 0).toFixed(2)}`;
const when = (iso) => (iso ? new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '');

export const JobInvoice = ({ jobId, hideWhenEmpty = false }) => {
  const { user } = useAuth();
  const [inv, setInv] = useState(null);
  const [failed, setFailed] = useState(false);
  const [sending, setSending] = useState(false);

  const load = useCallback(() => {
    setFailed(false);
    api.get(`/jobs/${jobId}/invoice`).then((r) => setInv(r.data)).catch(() => setFailed(true));
  }, [jobId]);

  useEffect(() => { setInv(null); load(); }, [load]);

  const send = async () => {
    setSending(true);
    try {
      const { data } = await api.post(`/jobs/${jobId}/invoice/send`);
      setInv(data);
      toast.success(data.email_sent ? 'Invoice sent in chat and by email' : 'Invoice sent in chat (email could not be delivered)');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not send invoice');
    } finally { setSending(false); }
  };

  if (failed) return null;
  if (!inv) return <div className="py-6 flex justify-center"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>;
  if (hideWhenEmpty && inv.lines.length === 0) return null;
  const isProvider = user?.user_id === inv.provider_id;

  return (
    <div className="bg-card border border-border rounded-2xl p-4 sm:p-5 min-w-0" data-testid="job-invoice">
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <Receipt className="w-4 h-4 text-primary" />
        <h3 className="font-semibold text-foreground">Job summary & invoice</h3>
        <span className="ml-auto text-xs text-muted-foreground">{inv.entries_count} time entries</span>
      </div>
      {inv.sent && <SentBadge sent={inv.sent} isProvider={isProvider} />}
      {inv.lines.length === 0 ? (
        <p className="text-sm text-muted-foreground" data-testid="invoice-empty">No billable items yet.</p>
      ) : (
        <div className="text-sm">
          {inv.lines.map((l, i) => (
            <div key={i} className="flex items-start justify-between gap-3 py-2 border-b border-border last:border-0" data-testid={`invoice-line-${l.kind}-${i}`}>
              <div className="min-w-0">
                <div className="font-medium text-foreground">{l.description}</div>
                {l.unit === 'hours' && <div className="text-xs text-muted-foreground">{l.quantity} h × {money(l.rate)}/h</div>}
              </div>
              <div className="font-medium tabular-nums shrink-0">{money(l.amount)}</div>
            </div>
          ))}
        </div>
      )}
      <div className="mt-3 pt-3 border-t border-border space-y-1 text-sm">
        <Row label="Subtotal" value={money(inv.subtotal)} testid="invoice-subtotal" />
        <Row label={`GST (${Math.round(inv.gst_rate * 100)}%)`} value={money(inv.gst)} testid="invoice-gst" />
        <div className="flex justify-between font-bold text-base pt-1"><span>Total</span><span data-testid="invoice-total" className="tabular-nums">{money(inv.total)}</span></div>
      </div>
      {!isProvider && inv.is_sent_copy && <PayInvoiceButton jobId={jobId} />}
      {isProvider && inv.payment_status === 'paid' && <div className="mt-3 text-sm font-medium text-emerald-600" data-testid="invoice-paid-provider">Paid by the client · 5% platform fee deducted from your payout</div>}
      {isProvider && inv.lines.length > 0 && inv.payment_status !== 'paid' && (
        <Button onClick={send} disabled={sending} className="w-full mt-4" data-testid="send-invoice-btn">
          {sending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
          {inv.sent ? 'Resend updated invoice' : 'Send invoice to customer'}
        </Button>
      )}
    </div>
  );
};

const SentBadge = ({ sent, isProvider }) => (
  <div className="mb-3 flex items-start gap-2 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-3 py-2 text-xs" data-testid="invoice-sent-badge">
    <CheckCircle2 className="w-4 h-4 shrink-0" />
    <span>
      {isProvider ? `Version ${sent.version} sent ${when(sent.sent_at)} · ${money(sent.total)}` : `Sent by your provider ${when(sent.sent_at)}${sent.version > 1 ? ` (updated, v${sent.version})` : ''}`}
      {isProvider && (sent.email_sent ? ' · emailed' : ' · in chat only')}
    </span>
  </div>
);

const Row = ({ label, value, testid }) => (
  <div className="flex justify-between text-muted-foreground"><span>{label}</span><span data-testid={testid} className="tabular-nums">{value}</span></div>
);

export default JobInvoice;
