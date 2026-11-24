import React, { useEffect, useState } from 'react';
import { Home as HomeIcon, Building2 } from 'lucide-react';
import api from '../lib/api';

export const PRICING_LABELS = { small_fixed: 'Small fixed', hourly: 'Hourly', large_quote: 'Project quote' };

/** Specialization badges grouped by track. Pass `specs` directly or a `providerId` to fetch them. */
export default function SpecializationBadges({ providerId, specs: given, compact = false, testid = 'specialization-badges' }) {
  const [specs, setSpecs] = useState(given || []);
  useEffect(() => {
    if (given) { setSpecs(given); return; }
    if (!providerId) return;
    api.get(`/providers/${providerId}/specializations`).then((r) => setSpecs(r.data || [])).catch(() => setSpecs([]));
  }, [providerId, given]);

  if (!specs.length) return null;
  const groups = ['residential', 'commercial'].map((t) => ({ t, items: specs.filter((s) => s.service_type === t) })).filter((g) => g.items.length);

  return (
    <div className="space-y-2" data-testid={testid}>
      {groups.map(({ t, items }) => {
        const Icon = t === 'commercial' ? Building2 : HomeIcon;
        return (
          <div key={t} className="flex flex-wrap items-center gap-1.5">
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mr-1">
              <Icon className="w-3 h-3" /> {t}
            </span>
            {items.map((s) => (
              <span
                key={`${s.service_type}-${s.category_id}-${s.subcategory_id}`}
                title={`${s.category_name} → ${s.subcategory_name}${s.pricing_modes ? ` · ${s.pricing_modes.map((m) => PRICING_LABELS[m]).join(', ')}` : ''}`}
                className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${t === 'commercial' ? 'border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-300' : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'}`}
              >
                {s.subcategory_name}
                {!compact && s.rate ? <span className="ml-1 opacity-70">· ${s.rate}</span> : null}
              </span>
            ))}
          </div>
        );
      })}
    </div>
  );
}
