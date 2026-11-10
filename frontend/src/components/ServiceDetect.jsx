import React, { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react';
import api from '../lib/api';

// Debounced guess of category/subcategory from free text.
export function useServiceDetect(text, serviceType) {
  const [result, setResult] = useState({ match: null, alternatives: [] });
  useEffect(() => {
    const t = (text || '').trim();
    if (t.length < 3) { setResult({ match: null, alternatives: [] }); return undefined; }
    const id = setTimeout(() => {
      api.get('/services/detect', { params: { text: t, service_type: serviceType } })
        .then((r) => setResult(r.data))
        .catch(() => {});
    }, 400);
    return () => clearTimeout(id);
  }, [text, serviceType]);
  return result;
}

export const DetectedAlternatives = ({ alternatives, onPick }) => {
  if (!alternatives?.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-2" data-testid="detected-alternatives">
      <span className="text-[11px] text-muted-foreground inline-flex items-center gap-1"><Sparkles className="w-3 h-3" /> Or did you mean</span>
      {alternatives.map((a) => (
        <button
          key={`${a.category_id}/${a.subcategory_id}`}
          type="button"
          onClick={() => onPick(a)}
          data-testid={`detected-alt-${a.subcategory_id}`}
          className="px-2.5 py-1 rounded-full bg-muted hover:bg-accent text-xs text-foreground transition-colors"
        >
          {a.subcategory_name}
        </button>
      ))}
    </div>
  );
};

export const providersLink = (p) => `/find-providers?${new URLSearchParams({
  category: p.category_id, subcategory: p.subcategory_id, category_name: p.category_name, subcategory_name: p.subcategory_name,
}).toString()}`;
