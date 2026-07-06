import React, { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, MapPin, Clock, DollarSign } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';

const statusColors = {
  open: 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300',
  in_progress: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
  done: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300',
  cancelled: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
};

const statusLabels = {
  open: 'Open', in_progress: 'In Progress', done: 'Done', cancelled: 'Cancelled',
};

const urgencyLabels = {
  asap: 'ASAP - Urgent',
  this_week: 'Within 1 week',
  within_month: 'Within a month',
  flexible: 'Flexible',
};

export default function MyJobPosts() {
  const [jobs, setJobs] = useState([]);
  const [filter, setFilter] = useState('all');
  const [selected, setSelected] = useState(null);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try {
      const res = await api.get('/jobs/mine');
      setJobs(res.data);
      if (res.data.length) setSelected((s) => s || res.data[0]);
    } catch (err) {
      console.error('[MyJobPosts] load failed:', err);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const counts = { all: jobs.length, open: jobs.filter((j) => j.status === 'open').length, in_progress: jobs.filter((j) => j.status === 'in_progress').length, done: jobs.filter((j) => j.status === 'done').length };
  const filtered = filter === 'all' ? jobs : jobs.filter((j) => j.status === filter);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">My Job Posts</h1>
          <p className="text-sm text-muted-foreground">{counts.open} open · {jobs.reduce((s, j) => s + (j.bids_count || 0), 0)} total bids received</p>
        </div>
        <Link to="/post-job">
          <Button><Plus className="w-4 h-4 mr-1" /> Post Job</Button>
        </Link>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
        {[
          { k: 'all', l: 'All' },
          { k: 'open', l: 'Open' },
          { k: 'in_progress', l: 'In Progress' },
          { k: 'done', l: 'Done' },
        ].map((f) => (
          <button key={f.k} onClick={() => setFilter(f.k)} className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${filter === f.k ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>
            {f.l} ({counts[f.k] || 0})
          </button>
        ))}
      </div>

      {jobs.length === 0 ? (
        <div className="bg-card border border-border rounded-2xl p-12 text-center">
          <div className="text-lg font-medium text-foreground">No job posts yet</div>
          <p className="text-sm text-muted-foreground mt-1">Post your first job to get matched with pros.</p>
          <Link to="/post-job"><Button className="mt-4">Post a Job</Button></Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
          <div className="space-y-2">
            {filtered.map((j) => (
              <button key={j.job_id} onClick={() => setSelected(j)} className={`w-full text-left p-4 rounded-xl border transition-all ${selected?.job_id === j.job_id ? 'border-primary bg-primary/5 shadow-sm' : 'border-border bg-card hover:border-primary/40'}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="font-semibold text-foreground flex-1 truncate">{j.title}</div>
                  <Badge className={statusColors[j.status]}>{statusLabels[j.status]}</Badge>
                </div>
                <div className="text-sm text-muted-foreground mt-1 line-clamp-2">{j.description}</div>
                <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1"><MapPin className="w-3 h-3" /> {j.location}</span>
                  <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" /> {urgencyLabels[j.urgency]}</span>
                  {j.budget_min && <span className="inline-flex items-center gap-1"><DollarSign className="w-3 h-3" /> {j.budget_min}-{j.budget_max}</span>}
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <div className="text-xs text-muted-foreground"><span className="font-semibold text-foreground">{j.bids_count || 0}</span> bids</div>
                  {j.bids_range && <div className="text-xs font-medium text-emerald-600">${j.bids_range.min}–${j.bids_range.max}</div>}
                </div>
              </button>
            ))}
          </div>

          <div className="bg-card border border-border rounded-2xl p-6">
            {selected ? <JobDetailPanel job={selected} onRefresh={load} onOpen={() => navigate(`/jobs/${selected.job_id}`)} /> : <div className="text-muted-foreground text-center py-10">Select a job to view details</div>}
          </div>
        </div>
      )}
    </div>
  );
}

function JobDetailPanel({ job, onRefresh, onOpen }) {
  const [bids, setBids] = useState([]);

  useEffect(() => {
    if (!job) return;
    api.get(`/jobs/${job.job_id}`).then((r) => setBids(r.data.bids || []));
  }, [job?.job_id]);

  const accept = async (bid) => {
    await api.post(`/bids/${bid.bid_id}/accept`);
    onRefresh();
  };

  return (
    <div>
      <div className="flex items-start justify-between">
        <h2 className="text-xl font-bold text-foreground">{job.title}</h2>
        <Badge className={statusColors[job.status]}>{statusLabels[job.status]}</Badge>
      </div>
      <p className="text-muted-foreground mt-2 text-sm">{job.description}</p>
      <Button size="sm" variant="outline" className="mt-3" onClick={onOpen}>Open full view</Button>

      <div className="mt-6">
        <div className="text-sm font-semibold text-foreground mb-3">Proposals ({bids.length})</div>
        {bids.length === 0 ? (
          <div className="text-center py-10 border border-dashed border-border rounded-xl">
            <div className="text-sm font-medium text-foreground">No proposals yet</div>
            <div className="text-xs text-muted-foreground">Providers will start submitting proposals soon. Check back shortly.</div>
          </div>
        ) : (
          <div className="space-y-3">
            {bids.map((b) => (
              <div key={b.bid_id} className="p-4 rounded-xl border border-border">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-medium text-foreground">{b.provider_name}</div>
                    <div className="text-xs text-muted-foreground">Rating {b.provider_rating} ★ · ETA {b.eta_days} days</div>
                  </div>
                  <div className="text-lg font-bold text-primary">${b.amount}</div>
                </div>
                <p className="text-sm text-muted-foreground mt-2">{b.message}</p>
                {b.status === 'pending' && job.status === 'open' && (
                  <div className="flex gap-2 mt-3">
                    <Button size="sm" onClick={() => accept(b)}>Accept Bid</Button>
                    <Button size="sm" variant="outline">Message</Button>
                  </div>
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
