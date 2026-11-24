import React from 'react';
import { MapPin, Clock, XCircle, Radio } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '../ui/badge';
import api from '../../lib/api';

export const STATUS_STYLE = {
  assigned: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
  in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300',
  done: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300',
  cancelled: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
};
export const hrs = (mins) => `${(Number(mins || 0) / 60).toFixed(1)} h`;

export const TeamAssignments = ({ items, onChange }) => {
  const cancel = async (a) => {
    try {
      await api.delete(`/team/assignments/${a.assignment_id}`);
      toast.success('Job taken back');
      onChange();
    } catch (e) { toast.error(e.response?.data?.detail || 'Could not cancel'); }
  };

  if (!items.length) {
    return <div className="bg-card border border-dashed border-border rounded-2xl p-10 text-center text-sm text-muted-foreground" data-testid="assignments-empty">No jobs sent yet. Use "Send job" on a team member.</div>;
  }
  return (
    <div className="space-y-2" data-testid="assignments-list">
      {items.map((a) => (
        <div key={a.assignment_id} className="bg-card border border-border rounded-2xl p-4 flex flex-wrap items-start gap-3" data-testid={`assignment-${a.assignment_id}`}>
          <div className="flex-1 min-w-[200px]">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-foreground">{a.title}</span>
              <Badge className={STATUS_STYLE[a.status]} data-testid="assignment-status">{a.status.replace('_', ' ')}</Badge>
              {a.clocked_in && <Badge className="bg-blue-600 text-white" data-testid="assignment-on-site"><Radio className="w-3 h-3 mr-1" /> on site</Badge>}
            </div>
            <div className="text-xs text-muted-foreground mt-1">To {a.member_name}{a.scheduled_for ? ` · ${new Date(a.scheduled_for).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}` : ''}</div>
            {a.address && <div className="text-xs text-muted-foreground mt-1 inline-flex items-center gap-1"><MapPin className="w-3 h-3" /> {a.address}</div>}
          </div>
          <div className="text-sm font-medium tabular-nums inline-flex items-center gap-1" data-testid="assignment-hours"><Clock className="w-3.5 h-3.5 text-muted-foreground" /> {hrs(a.minutes_logged)}</div>
          {['assigned', 'in_progress'].includes(a.status) && (
            <button onClick={() => cancel(a)} className="p-1 text-muted-foreground hover:text-destructive" aria-label="Take job back" data-testid="assignment-cancel-btn"><XCircle className="w-4 h-4" /></button>
          )}
        </div>
      ))}
    </div>
  );
};

export default TeamAssignments;
