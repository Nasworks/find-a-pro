import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Zap, Trophy, MessageSquare, CheckCircle2, XCircle } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import api from '../lib/api';

const ICONS = { job_match: Zap, job_awarded: Trophy, match_response: MessageSquare, job_status: CheckCircle2, job_closed: XCircle };

const ago = (iso) => {
  const s = (Date.now() - new Date(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`).getTime()) / 1000;
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
};

export default function NotificationBell({ className = '', testid = 'notifications-btn' }) {
  const navigate = useNavigate();
  const [data, setData] = useState({ unread: 0, items: [] });
  const [open, setOpen] = useState(false);

  const load = useCallback(() => {
    api.get('/notifications/mine').then((r) => setData(r.data)).catch(() => {});
  }, []);
  useEffect(() => {
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [load]);

  const onOpenChange = (o) => {
    setOpen(o);
    if (o) load();
    if (!o && data.unread) {
      api.post('/notifications/read-all').then(load).catch(() => {});
    }
  };

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>
        <button className={`relative flex items-center justify-center rounded-full hover:bg-accent transition-colors ${className}`} aria-label="Notifications" data-testid={testid}>
          <Bell className="w-5 h-5 text-muted-foreground" />
          {data.unread > 0 && (
            <span className="absolute top-1 right-1 min-w-[16px] h-4 px-1 rounded-full bg-primary text-primary-foreground text-[10px] font-semibold flex items-center justify-center" data-testid="notifications-unread">
              {data.unread > 9 ? '9+' : data.unread}
            </span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0" data-testid="notifications-panel">
        <div className="px-4 py-3 border-b border-border font-semibold text-sm text-foreground">Notifications</div>
        <div className="max-h-96 overflow-y-auto">
          {data.items.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">You're all caught up</div>
          ) : data.items.map((n) => {
            const Icon = ICONS[n.type] || Bell;
            return (
              <button
                key={n.notification_id}
                type="button"
                onClick={() => { setOpen(false); if (n.link) navigate(n.link); }}
                className={`w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-accent border-b border-border/60 last:border-0 ${n.read ? '' : 'bg-primary/5'}`}
              >
                <span className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0"><Icon className="w-4 h-4" /></span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-foreground">{n.title}</span>
                  {n.body && <span className="block text-xs text-muted-foreground truncate">{n.body}</span>}
                  <span className="block text-[11px] text-muted-foreground mt-0.5">{ago(n.created_at)}</span>
                </span>
                {!n.read && <span className="w-2 h-2 rounded-full bg-primary mt-2 shrink-0" />}
              </button>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}
