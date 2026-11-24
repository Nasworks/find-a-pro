import React, { useCallback, useEffect, useState } from 'react';
import { Check, Loader2, Send, Flag } from 'lucide-react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { MediaUploader, MediaThumb } from './MediaUploader';
import api from '../lib/api';
import { toast } from 'sonner';

const when = (iso) => new Date(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`).toLocaleString('en-NZ', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });

/** Stage stepper + update feed. The assigned provider can move the stage and send updates to the client. */
export default function ProjectTimeline({ jobId, compact = false, onChanged }) {
  const [data, setData] = useState(null);
  const [stage, setStage] = useState(null);
  const [msg, setMsg] = useState('');
  const [photos, setPhotos] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.get(`/jobs/${jobId}/timeline`).then((r) => { setData(r.data); setStage(r.data.current_stage); }).catch(() => setData(null));
  }, [jobId]);
  useEffect(() => { load(); }, [load]);
  if (!data) return null;

  const send = async () => {
    setBusy(true);
    try {
      await api.post(`/jobs/${jobId}/timeline`, {
        stage_index: stage !== data.current_stage ? stage : null, message: msg, photos, notify_client: true,
      });
      toast.success('Update sent to the client');
      setMsg(''); setPhotos([]);
      load(); onChanged?.();
    } catch (err) { toast.error(err?.response?.data?.detail || 'Could not send update'); } finally { setBusy(false); }
  };

  const updates = compact ? data.updates.slice(0, 3) : data.updates;
  return (
    <div className="space-y-4" data-testid={`project-timeline-${jobId}`}>
      <ol className="flex items-start gap-1 overflow-x-auto pb-1" data-testid="timeline-stages">
        {data.stages.map((s, i) => {
          const done = i < data.current_stage;
          const cur = i === data.current_stage;
          const picked = data.can_edit && i === stage && stage !== data.current_stage;
          return (
            <li key={s} className="flex-1 min-w-[72px]">
              <button type="button" disabled={!data.can_edit} onClick={() => setStage(i)} data-testid={`timeline-stage-${i}`}
                className={`w-full text-left ${data.can_edit ? 'cursor-pointer' : 'cursor-default'}`}>
                <div className={`h-1.5 rounded-full ${done || cur ? 'bg-primary' : picked ? 'bg-primary/40' : 'bg-muted'}`} />
                <div className="flex items-center gap-1 mt-1.5">
                  {done ? <Check className="w-3 h-3 text-primary shrink-0" /> : cur ? <Flag className="w-3 h-3 text-primary shrink-0" /> : null}
                  <span className={`text-[11px] leading-tight ${cur ? 'text-foreground font-semibold' : picked ? 'text-primary font-medium' : 'text-muted-foreground'}`}>{s}</span>
                </div>
              </button>
            </li>
          );
        })}
      </ol>

      {data.can_edit && (
        <div className="rounded-xl border border-border p-3 space-y-2 bg-background" data-testid="timeline-composer">
          {stage !== data.current_stage && <div className="text-xs text-primary">Moving to: <strong>{data.stages[stage]}</strong></div>}
          <Textarea rows={2} value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Send the client an update — what's done, what's next…" data-testid="timeline-message" />
          <MediaUploader value={photos} onChange={setPhotos} testid="timeline-media" />
          <Button size="sm" onClick={send} disabled={busy || (!msg.trim() && !photos.length && stage === data.current_stage)} data-testid="timeline-send">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Send className="w-3.5 h-3.5 mr-1" /> Send update to client</>}
          </Button>
        </div>
      )}

      <div className="space-y-3" data-testid="timeline-updates">
        {updates.map((u) => (
          <div key={u.update_id} className="flex gap-3">
            <div className="w-2 h-2 rounded-full bg-primary mt-1.5 shrink-0" />
            <div className="min-w-0 flex-1">
              <div className="text-xs text-muted-foreground">{when(u.created_at)} · {u.author_name}{u.stage_changed ? <> · moved to <strong className="text-foreground">{u.stage}</strong></> : ''}</div>
              {u.message && <div className="text-sm text-foreground mt-0.5 whitespace-pre-wrap">{u.message}</div>}
              {u.photos?.length > 0 && <div className="flex gap-2 mt-2 flex-wrap">{u.photos.map((p) => <span key={p} className="w-16 h-16 rounded-lg overflow-hidden border border-border block"><MediaThumb url={p} /></span>)}</div>}
            </div>
          </div>
        ))}
        {data.updates.length === 0 && <div className="text-xs text-muted-foreground">No updates yet</div>}
      </div>
    </div>
  );
}
