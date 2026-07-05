import React, { useEffect, useState } from 'react';
import { ExternalLink, MapPin, DollarSign, Clock, Filter } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';
import { toast } from 'sonner';

const sourceColors = {
  'Builderscrack': 'bg-orange-100 text-orange-700 dark:bg-orange-950/60 dark:text-orange-300',
  'NoCowboys': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300',
  'Neighbourly': 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300',
  'Trade Me': 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300',
};

export default function ExternalJobs() {
  const [jobs, setJobs] = useState([]);
  const [selectedSource, setSelectedSource] = useState(null);

  useEffect(() => {
    api.get('/external-jobs').then((r) => setJobs(r.data));
  }, []);

  const sources = [...new Set(jobs.map((j) => j.source))];
  const filtered = selectedSource ? jobs.filter((j) => j.source === selectedSource) : jobs;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">External Jobs</h1>
        <p className="text-sm text-muted-foreground">Leads aggregated from partner platforms · Refreshed every 15 min</p>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
        <button onClick={() => setSelectedSource(null)} className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${!selectedSource ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>All sources</button>
        {sources.map((s) => (
          <button key={s} onClick={() => setSelectedSource(s)} className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${selectedSource === s ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>{s}</button>
        ))}
      </div>

      <div className="space-y-3">
        {filtered.length === 0 && <div className="text-center py-16 text-muted-foreground">No external jobs available</div>}
        {filtered.map((j) => (
          <div key={j.external_id} className="bg-card border border-border rounded-2xl p-5 hover:border-primary/40 transition-colors">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge className={sourceColors[j.source] || 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'}>{j.source}</Badge>
                  <span className="text-xs text-muted-foreground capitalize">{j.category}</span>
                </div>
                <h3 className="font-semibold text-foreground mt-1.5">{j.title}</h3>
                <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{j.description}</p>
                <div className="flex flex-wrap gap-3 mt-3 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1"><MapPin className="w-3 h-3" /> {j.location}</span>
                  <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" /> {j.posted}</span>
                </div>
              </div>
              <div className="text-right shrink-0 ml-4">
                <div className="text-sm font-bold text-primary">{j.budget}</div>
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <Button size="sm" className="flex-1" onClick={() => toast.info('External link opens on source site')}><ExternalLink className="w-3.5 h-3.5 mr-1" /> View on {j.source}</Button>
              <Button size="sm" variant="outline" className="flex-1" onClick={() => toast.success('Lead saved to your dashboard')}>Save Lead</Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
