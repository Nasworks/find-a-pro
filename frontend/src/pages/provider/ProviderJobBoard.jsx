import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapPin, Clock, DollarSign, Search } from 'lucide-react';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import api from '../../lib/api';
import { formatDistanceToNow } from 'date-fns';

export default function ProviderJobBoard() {
  const [jobs, setJobs] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCat, setSelectedCat] = useState(null);
  const [query, setQuery] = useState('');

  useEffect(() => {
    api.get('/categories').then((r) => setCategories(r.data));
  }, []);

  useEffect(() => {
    const params = {};
    if (selectedCat) params.category = selectedCat;
    api.get('/jobs/board', { params }).then((r) => setJobs(r.data));
  }, [selectedCat]);

  const filtered = jobs.filter((j) => !query || j.title.toLowerCase().includes(query.toLowerCase()) || j.description.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Job Board</h1>
        <p className="text-sm text-muted-foreground">Open jobs from customers near you</p>
      </div>

      <div className="mb-4 relative max-w-lg">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search jobs..." className="w-full pl-10 pr-4 py-2 rounded-lg bg-muted/40 border border-transparent focus:border-primary/40 focus:bg-background outline-none text-sm" />
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        <button onClick={() => setSelectedCat(null)} className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${!selectedCat ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>All</button>
        {categories.map((c) => (
          <button key={c.id} onClick={() => setSelectedCat(c.id)} className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${selectedCat === c.id ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>{c.name}</button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered.length === 0 && <div className="col-span-2 text-center py-16 text-muted-foreground">No open jobs matching your filters.</div>}
        {filtered.map((j) => (
          <Link to={`/jobs/${j.job_id}`} key={j.job_id} className="block bg-card border border-border rounded-2xl p-5 hover:border-primary/40 hover:shadow-md transition-all">
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-semibold text-foreground">{j.title}</h3>
              <Badge variant="secondary" className="capitalize">{j.urgency.replace('_', ' ')}</Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{j.description}</p>
            <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-muted-foreground">
              <span className="capitalize">{j.category}</span>
              <span className="inline-flex items-center gap-1"><MapPin className="w-3 h-3" /> {j.location}</span>
              {j.budget_min && <span className="inline-flex items-center gap-1"><DollarSign className="w-3 h-3" /> ${j.budget_min}–{j.budget_max}</span>}
              <span className="inline-flex items-center gap-1 ml-auto"><Clock className="w-3 h-3" /> {formatDistanceToNow(new Date(j.created_at), { addSuffix: true })}</span>
            </div>
            <Button size="sm" className="mt-4 w-full">View & Bid</Button>
          </Link>
        ))}
      </div>
    </div>
  );
}
