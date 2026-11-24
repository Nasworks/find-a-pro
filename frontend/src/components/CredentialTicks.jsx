import React, { useEffect, useState } from 'react';
import { ShieldCheck, GraduationCap, BadgeCheck, Clock } from 'lucide-react';
import api from '../lib/api';

/** Verified ticks on a provider profile — only shown once a reviewer approves the document. */
export default function CredentialTicks({ providerId, data: given, showPending = false, className = '' }) {
  const [data, setData] = useState(given || null);
  useEffect(() => {
    if (given) { setData(given); return; }
    if (!providerId) return;
    api.get(`/providers/${providerId}/credentials`).then((r) => setData(r.data)).catch(() => setData(null));
  }, [providerId, given]);
  if (!data) return null;
  const Tick = ({ on, icon: Icon, label, testid }) => (
    <span data-testid={testid} className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${on ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' : 'bg-muted text-muted-foreground'}`}>
      {on ? <BadgeCheck className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
      <Icon className="w-3 h-3 opacity-70" /> {label}{on ? '' : ' — not yet verified'}
    </span>
  );
  if (!showPending && !data.qualified && !data.police_checked) return null;
  return (
    <div className={`flex flex-wrap gap-1.5 ${className}`} data-testid="credential-ticks">
      {(data.qualified || showPending) && <Tick on={data.qualified} icon={GraduationCap} label="Qualifications verified" testid="tick-qualified" />}
      {(data.police_checked || showPending) && <Tick on={data.police_checked} icon={ShieldCheck} label="Police checked" testid="tick-police" />}
    </div>
  );
}
