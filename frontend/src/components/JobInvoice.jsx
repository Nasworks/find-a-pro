import React, { useEffect, useState } from 'react';
import { Receipt, Loader2 } from 'lucide-react';
import api from '../lib/api';

const money = (n) => `$${Number(n || 0).toFixed(2)}`;

export const JobInvoice = ({ jobId, hideWhenEmpty = false }) => {
  const [inv, setInv] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setInv(null);
    setFailed(false);
    api.get(`/jobs/${jobId}/invoice`).then((r) => setInv(r.data)).catch(() => setFailed(true));
  }, [jobId]);

  if (failed) return null;
  if (!inv) return <div className="py-6 flex justify-center"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>;
  if (hideWhenEmpty && inv.lines.length === 0) return null;

  return (
    <div className="bg-card border border-border rounded-2xl p-5" data-testid="job-invoice">
      <div className="flex items-center gap-2 mb-3">
        <Receipt className="w-4 h-4 text-primary" />
        <h3 className="font-semibold text-foreground">Job summary & invoice</h3>
        <span className="ml-auto text-xs text-muted-foreground">{inv.entries_count} time entries</span>
      </div>
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
    </div>
  );
};

const Row = ({ label, value, testid }) => (
  <div className="flex justify-between text-muted-foreground"><span>{label}</span><span data-testid={testid} className="tabular-nums">{value}</span></div>
);

export default JobInvoice;
