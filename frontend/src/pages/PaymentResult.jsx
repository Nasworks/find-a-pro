import React, { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CheckCircle2, Loader2, XCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import api from '../lib/api';

export function PaymentSuccess() {
  const [params] = useSearchParams();
  const sessionId = params.get('session_id');
  const [state, setState] = useState({ status: 'checking', jobId: null });
  const tries = useRef(0);

  useEffect(() => {
    if (!sessionId) { setState({ status: 'error' }); return undefined; }
    let timer;
    const poll = async () => {
      try {
        const r = await api.get(`/payments/status/${sessionId}`);
        if (r.data.payment_status === 'paid') { setState({ status: 'paid', jobId: r.data.job_id }); return; }
        if (r.data.status === 'expired') { setState({ status: 'expired', jobId: r.data.job_id }); return; }
        setState({ status: 'checking', jobId: r.data.job_id });
      } catch (err) {
        if (err?.response?.status === 404) { setState({ status: 'error' }); return; }
      }
      tries.current += 1;
      if (tries.current < 15) timer = setTimeout(poll, 2000);
      else setState((s) => ({ ...s, status: 'timeout' }));
    };
    poll();
    return () => clearTimeout(timer);
  }, [sessionId]);

  const paid = state.status === 'paid';
  return (
    <div className="min-h-[70vh] flex items-center justify-center p-6" data-testid="payment-success">
      <div className="bg-card border border-border rounded-2xl p-8 max-w-md w-full text-center">
        {state.status === 'checking' && <Loader2 className="w-10 h-10 animate-spin text-primary mx-auto" />}
        {paid && <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto" />}
        {['expired', 'error', 'timeout'].includes(state.status) && <XCircle className="w-12 h-12 text-rose-500 mx-auto" />}
        <h1 className="text-2xl font-bold text-foreground mt-4" data-testid="payment-status-title">
          {paid ? 'Payment received' : state.status === 'checking' ? 'Confirming your payment…' : state.status === 'timeout' ? 'Still processing' : 'Payment not completed'}
        </h1>
        <p className="text-sm text-muted-foreground mt-2">
          {paid ? 'Your job is marked as paid and moved to your history.' : state.status === 'timeout' ? 'Stripe is still confirming — check the job again in a minute.' : state.status === 'checking' ? 'This usually takes a few seconds.' : 'No money was taken. You can try again from the invoice.'}
        </p>
        {state.jobId && <Button asChild className="mt-6"><Link to={`/jobs/${state.jobId}`}>Back to the job</Link></Button>}
      </div>
    </div>
  );
}

export function PaymentCancel() {
  const [params] = useSearchParams();
  const jobId = params.get('job_id');
  return (
    <div className="min-h-[70vh] flex items-center justify-center p-6" data-testid="payment-cancel">
      <div className="bg-card border border-border rounded-2xl p-8 max-w-md w-full text-center">
        <XCircle className="w-12 h-12 text-muted-foreground mx-auto" />
        <h1 className="text-2xl font-bold text-foreground mt-4">Payment cancelled</h1>
        <p className="text-sm text-muted-foreground mt-2">No money was taken. You can pay any time from the invoice.</p>
        {jobId && <Button asChild className="mt-6"><Link to={`/jobs/${jobId}`}>Back to the job</Link></Button>}
      </div>
    </div>
  );
}
