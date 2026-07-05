import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, MapPin, Clock, DollarSign } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import api from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'sonner';

export default function JobDetail() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [bidForm, setBidForm] = useState({ amount: '', message: '', eta_days: 3 });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      const r = await api.get(`/jobs/${jobId}`);
      setData(r.data);
    } catch {
      toast.error('Job not found');
      navigate(-1);
    }
  };
  useEffect(() => { load(); }, [jobId]);

  const submitBid = async (e) => {
    e.preventDefault();
    if (!bidForm.amount || !bidForm.message) return;
    setSaving(true);
    try {
      await api.post('/bids', { ...bidForm, job_id: jobId, amount: Number(bidForm.amount), eta_days: Number(bidForm.eta_days) });
      toast.success('Bid submitted');
      setBidForm({ amount: '', message: '', eta_days: 3 });
      load();
    } catch {
      toast.error('Failed to submit bid');
    } finally { setSaving(false); }
  };

  const acceptBid = async (bid_id) => {
    await api.post(`/bids/${bid_id}/accept`);
    toast.success('Bid accepted — booking created');
    load();
  };

  if (!data) return <div className="p-10 text-center text-muted-foreground">Loading...</div>;
  const { job, bids } = data;
  const isOwner = user?.user_id === job.client_id;
  const alreadyBid = bids.some((b) => b.provider_id === user?.user_id);

  return (
    <div className="max-w-4xl mx-auto p-6">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      <div className="bg-card border border-border rounded-2xl p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">{job.title}</h1>
            <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1"><MapPin className="w-3.5 h-3.5" /> {job.location}</span>
              <span className="inline-flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> {job.urgency}</span>
              {job.budget_min && <span className="inline-flex items-center gap-1"><DollarSign className="w-3.5 h-3.5" /> ${job.budget_min} – ${job.budget_max}</span>}
            </div>
          </div>
          <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 capitalize">{job.status.replace('_', ' ')}</Badge>
        </div>
        <p className="mt-4 text-foreground/90 whitespace-pre-wrap">{job.description}</p>
      </div>

      {!isOwner && user?.role === 'provider' && job.status === 'open' && !alreadyBid && (
        <form onSubmit={submitBid} className="mt-6 bg-card border border-border rounded-2xl p-6">
          <div className="font-semibold text-foreground mb-3">Submit your bid</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input type="number" placeholder="Your price ($)" value={bidForm.amount} onChange={(e) => setBidForm({ ...bidForm, amount: e.target.value })} required />
            <Input type="number" placeholder="ETA (days)" value={bidForm.eta_days} onChange={(e) => setBidForm({ ...bidForm, eta_days: e.target.value })} required />
          </div>
          <Textarea className="mt-3" rows={3} placeholder="Message to the customer" value={bidForm.message} onChange={(e) => setBidForm({ ...bidForm, message: e.target.value })} required />
          <Button className="mt-3" disabled={saving} type="submit">{saving ? 'Submitting...' : 'Submit Bid'}</Button>
        </form>
      )}

      <div className="mt-6">
        <h2 className="font-semibold text-foreground mb-3">Proposals ({bids.length})</h2>
        {bids.length === 0 ? (
          <div className="bg-card border border-dashed border-border rounded-xl p-8 text-center text-sm text-muted-foreground">No proposals yet</div>
        ) : (
          <div className="space-y-3">
            {bids.map((b) => (
              <div key={b.bid_id} className="p-4 bg-card border border-border rounded-xl">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-medium text-foreground">{b.provider_name}</div>
                    <div className="text-xs text-muted-foreground">Rating {b.provider_rating} ★ · ETA {b.eta_days} days</div>
                  </div>
                  <div className="text-lg font-bold text-primary">${b.amount}</div>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{b.message}</p>
                {isOwner && b.status === 'pending' && job.status === 'open' && (
                  <Button size="sm" onClick={() => acceptBid(b.bid_id)} className="mt-3">Accept Bid</Button>
                )}
                {b.status === 'accepted' && <Badge className="mt-2 bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">Accepted</Badge>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
