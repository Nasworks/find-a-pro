import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FolderKanban, MapPin, Loader2 } from 'lucide-react';
import { Badge } from '../../components/ui/badge';
import ProjectTimeline from '../../components/ProjectTimeline';
import api from '../../lib/api';

export default function ActiveProjects() {
  const [jobs, setJobs] = useState(null);
  const load = useCallback(() => {
    api.get('/matches/mine').then((r) => setJobs((r.data || []).filter((m) => m.match_status === 'awarded' && ['assigned', 'in_progress'].includes(m.job.status)).map((m) => m.job)))
      .catch(() => setJobs([]));
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 space-y-5" data-testid="active-projects">
      <div className="flex items-center gap-2">
        <FolderKanban className="w-6 h-6 text-primary" />
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground">Active projects</h1>
          <p className="text-sm text-muted-foreground">Track each active job's stage and keep your clients updated.</p>
        </div>
      </div>
      {jobs === null ? <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /> : jobs.length === 0 ? (
        <div className="text-sm text-muted-foreground text-center py-12 bg-card border border-dashed border-border rounded-2xl">No active jobs right now — jobs you're awarded appear here.</div>
      ) : jobs.map((j) => (
        <div key={j.job_id} className="bg-card border border-border rounded-2xl p-5" data-testid={`project-card-${j.job_id}`}>
          <div className="flex items-start justify-between gap-3 mb-4">
            <div className="min-w-0">
              <Link to={`/jobs/${j.job_id}`} className="font-semibold text-foreground hover:text-primary">{j.title}</Link>
              <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5"><MapPin className="w-3 h-3" /> <span className="truncate">{j.location}</span></div>
            </div>
            <Badge variant="outline" className="shrink-0 capitalize">{j.status.replace('_', ' ')}</Badge>
          </div>
          <ProjectTimeline jobId={j.job_id} onChanged={load} />
        </div>
      ))}
    </div>
  );
}
