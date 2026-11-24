import React, { useEffect, useState } from 'react';
import { CreditCard, Loader2, CheckCircle2, Info } from 'lucide-react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import api from '../lib/api';
import { toast } from 'sonner';

const money = (n) => `$${Number(n || 0).toFixed(2)}`;

/** Client "Pay now" with full fee disclosure (5% platform fee + Stripe card fee). */
export default function PayInvoiceButton({ jobId }) {
  const [quote, setQuote] = useState(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get(`/payments/invoice/${jobId}/quote`).then((r) => setQuote(r.data)).catch(() => setQuote(null));
  }, [jobId]);

  if (!quote) return null;
  if (quote.paid) {
    return (
      <div className="mt-4 flex items-center gap-2 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 px-4 py-3 text-sm font-medium" data-testid="invoice-paid">
        <CheckCircle2 className="w-4 h-4" /> Paid — thank you!
      </div>
    );
  }

  const pay = async () => {
    setBusy(true);
    try {
      const r = await api.post(`/payments/invoice/${jobId}/checkout`, { origin_url: window.location.origin });
      window.location.href = r.data.checkout_url;
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not start payment');
      setBusy(false);
    }
  };

  return (
    <>
      <Button className="w-full mt-4 h-11" onClick={() => setOpen(true)} data-testid="invoice-pay-btn">
        <CreditCard className="w-4 h-4 mr-2" /> Pay {money(quote.total_charge)}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md" data-testid="pay-disclosure">
          <DialogHeader>
            <DialogTitle>Review your payment</DialogTitle>
            <DialogDescription>Pay securely by card, Google Pay or Apple Pay through Stripe.</DialogDescription>
          </DialogHeader>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-muted-foreground">Invoice total (incl. GST)</span><span className="tabular-nums">{money(quote.invoice_total)}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Pro Finder platform fee (5%)</span><span className="tabular-nums" data-testid="pay-client-fee">{money(quote.client_platform_fee)}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">{quote.card_fee_note}</span><span className="tabular-nums" data-testid="pay-card-fee">{money(quote.card_fee)}</span></div>
            <div className="flex justify-between font-bold text-base border-t border-border pt-2"><span>You pay</span><span className="tabular-nums" data-testid="pay-total">{money(quote.total_charge)}</span></div>
          </div>
          <div className="flex gap-2 rounded-lg bg-muted p-3 text-xs text-muted-foreground">
            <Info className="w-4 h-4 shrink-0 mt-0.5" />
            <span>Card processing fees are charged by Stripe and passed on at cost. Your provider also pays a 5% platform fee out of their payout.</span>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" className="flex-1" onClick={() => setOpen(false)}>Cancel</Button>
            <Button className="flex-1" onClick={pay} disabled={busy} data-testid="pay-confirm">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Pay {money(quote.total_charge)}</>}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
