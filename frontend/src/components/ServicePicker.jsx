import React, { useEffect, useMemo, useState } from 'react';
import * as LucideIcons from 'lucide-react';
import { ChevronRight, Search, X, Building2, Home, Check, Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import api from '../lib/api';
import { useViewMode } from '../context/ViewModeContext';

/**
 * ServicePicker
 * Rich hierarchical service picker for the residential (18 cats) OR commercial (15 cats) taxonomies.
 *
 * Props:
 *   open, onOpenChange     — dialog control
 *   serviceType            — 'residential' | 'commercial'
 *   value                  — { category_id, subcategory_id } (optional, pre-highlights)
 *   onSelect               — callback with { category_id, category_name, category_icon, category_color, subcategory_id, subcategory_name }
 */
export default function ServicePicker({ open, onOpenChange, serviceType = 'residential', value, onSelect }) {
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [activeCat, setActiveCat] = useState(null);
  const [q, setQ] = useState('');
  const [meta, setMeta] = useState({ total_categories: 0, total_subcategories: 0 });
  const { isMobile } = useViewMode();

  const isCommercial = serviceType === 'commercial';

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    api.get(`/services/taxonomy/${serviceType}`)
      .then((r) => {
        setCategories(r.data.categories);
        setMeta({ total_categories: r.data.total_categories, total_subcategories: r.data.total_subcategories });
        if (value?.category_id) {
          setActiveCat(r.data.categories.find((c) => c.id === value.category_id) || r.data.categories[0]);
        } else {
          setActiveCat(r.data.categories[0]);
        }
      })
      .catch(() => setCategories([]))
      .finally(() => setLoading(false));
  }, [open, serviceType, value?.category_id]);

  const filtered = useMemo(() => {
    if (!q.trim()) return null;
    const term = q.toLowerCase();
    const results = [];
    categories.forEach((c) => {
      const catMatch = c.name.toLowerCase().includes(term);
      const matches = c.subcategories.filter((s) => s.name.toLowerCase().includes(term));
      if (catMatch || matches.length) results.push({ category: c, matches: matches.length ? matches : c.subcategories });
    });
    return results;
  }, [q, categories]);

  const pick = (cat, sub) => {
    onSelect?.({
      category_id: cat.id,
      category_name: cat.name,
      category_icon: cat.icon,
      category_color: cat.color,
      subcategory_id: sub.id,
      subcategory_name: sub.name,
    });
    onOpenChange(false);
  };

  const HeaderIcon = isCommercial ? Building2 : Home;
  const label = isCommercial ? 'Commercial Services' : 'Residential Home Services';
  const gradient = isCommercial ? 'from-primary/5 via-blue-500/5' : 'from-emerald-500/5 via-primary/5';
  const chipCls = isCommercial ? 'bg-primary/10 text-primary border-primary/20' : 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl p-0 gap-0 overflow-hidden max-h-[85vh]" data-testid={`service-picker-${serviceType}`}>
        <DialogHeader className={`p-5 pb-3 border-b border-border bg-gradient-to-r ${gradient} to-transparent`}>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isCommercial ? 'bg-primary/10 text-primary' : 'bg-emerald-500/10 text-emerald-600'}`}>
              <HeaderIcon className="w-4 h-4" />
            </div>
            {label}
            <Badge className={`ml-1 ${chipCls}`}>{meta.total_categories} categories · {meta.total_subcategories}+ services</Badge>
          </DialogTitle>
          <DialogDescription className="sr-only">Browse or search {label.toLowerCase()} — pick a category on the left, then a specific service on the right.</DialogDescription>
        </DialogHeader>

        {/* Search bar */}
        <div className="p-4 border-b border-border">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              data-testid="service-picker-search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={isCommercial ? "Search — 'LED', 'roof', 'CCTV', 'HVAC'..." : "Search — 'heat pump', 'painting', 'blocked drain'..."}
              className="pl-9 pr-9"
              autoFocus
            />
            {q && (
              <button onClick={() => setQ('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground" aria-label="Clear">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {loading ? (
          <div className="p-16 flex items-center justify-center text-muted-foreground">
            <Loader2 className="w-5 h-5 animate-spin" />
          </div>
        ) : filtered ? (
          /* SEARCH RESULTS VIEW */
          <div className="p-4 overflow-y-auto max-h-[60vh]">
            {filtered.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground">
                <Search className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <div className="text-sm">No services match "{q}"</div>
                <p className="text-xs mt-1">Try broader terms like "electrical" or "kitchen"</p>
              </div>
            ) : (
              <div className="space-y-4">
                {filtered.map(({ category: c, matches }) => (
                  <div key={c.id}>
                    <div className="flex items-center gap-2 mb-2">
                      <CategoryIconChip icon={c.icon} color={c.color} />
                      <div className="text-sm font-semibold text-foreground">{c.name}</div>
                      <span className="text-xs text-muted-foreground">({matches.length} match{matches.length === 1 ? '' : 'es'})</span>
                    </div>
                    <div className="grid sm:grid-cols-2 gap-1.5 pl-9">
                      {matches.map((s) => (
                        <button
                          key={s.id}
                          data-testid={`service-picker-sub-${c.id}-${s.id}`}
                          onClick={() => pick(c, s)}
                          className="text-left px-3 py-2 rounded-lg text-sm text-foreground hover:bg-accent hover:text-primary transition-colors flex items-center gap-2 group"
                        >
                          <span className="flex-1 truncate"><HighlightText text={s.name} query={q} /></span>
                          <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          /* BROWSE VIEW — stacks on mobile, 2-panel on desktop */
          <div className={isMobile ? 'flex flex-col overflow-hidden max-h-[65vh]' : 'grid grid-cols-[240px_1fr] overflow-hidden max-h-[60vh]'}>
            <div className={isMobile
              ? 'border-b border-border overflow-x-auto bg-muted/20 flex shrink-0'
              : 'border-r border-border overflow-y-auto bg-muted/20'}>
              {categories.map((c) => {
                const active = activeCat?.id === c.id;
                return (
                  <button
                    key={c.id}
                    data-testid={`service-picker-cat-${c.id}`}
                    onClick={() => setActiveCat(c)}
                    className={isMobile
                      ? `flex items-center gap-2 px-3 py-2 text-sm shrink-0 whitespace-nowrap border-b-2 transition-colors ${active ? 'text-foreground font-semibold border-b-primary bg-background' : 'text-muted-foreground border-b-transparent hover:text-foreground'}`
                      : `w-full flex items-center gap-2.5 px-3 py-2.5 text-left text-sm transition-colors border-l-2 ${active ? 'bg-background border-l-primary text-foreground font-semibold' : 'border-l-transparent text-muted-foreground hover:text-foreground hover:bg-background/60'}`}
                  >
                    <CategoryIconChip icon={c.icon} color={c.color} small />
                    <span className={isMobile ? '' : 'flex-1 truncate'}>{c.name}</span>
                    {value?.category_id === c.id && <Check className="w-3.5 h-3.5 text-primary shrink-0" />}
                  </button>
                );
              })}
            </div>

            <div className="overflow-y-auto p-4">
              {activeCat && (
                <>
                  <div className="flex items-center gap-2.5 mb-3 pb-3 border-b border-border">
                    <CategoryIconChip icon={activeCat.icon} color={activeCat.color} />
                    <div>
                      <div className="font-semibold text-foreground">{activeCat.name}</div>
                      <div className="text-xs text-muted-foreground">{activeCat.subcategories.length} services</div>
                    </div>
                  </div>
                  <div className={isMobile ? 'grid grid-cols-1 gap-1.5' : 'grid grid-cols-2 gap-1.5'}>
                    {activeCat.subcategories.map((s) => {
                      const selected = value?.category_id === activeCat.id && value?.subcategory_id === s.id;
                      return (
                        <button
                          key={s.id}
                          data-testid={`service-picker-sub-${activeCat.id}-${s.id}`}
                          onClick={() => pick(activeCat, s)}
                          className={`text-left px-3 py-2.5 rounded-lg text-sm transition-colors flex items-center gap-2 group border ${selected ? 'border-primary bg-primary/5 text-primary font-semibold' : 'border-transparent text-foreground hover:bg-accent hover:border-border'}`}
                        >
                          <span className="flex-1 truncate">{s.name}</span>
                          {selected ? <Check className="w-4 h-4 text-primary shrink-0" /> : <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />}
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        <div className="p-3 border-t border-border bg-muted/30 flex items-center justify-between text-xs text-muted-foreground">
          <span>Tip: type to search across all {meta.total_subcategories}+ services</span>
          <Button size="sm" variant="ghost" onClick={() => onOpenChange(false)}>Close</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function CategoryIconChip({ icon, color, small = false }) {
  const Icon = LucideIcons[icon] || LucideIcons.Wrench;
  const size = small ? 22 : 28;
  const iSize = small ? 'w-3 h-3' : 'w-3.5 h-3.5';
  return (
    <div className="rounded-md flex items-center justify-center text-white shrink-0" style={{ backgroundColor: color, width: size, height: size }}>
      <Icon className={iSize} />
    </div>
  );
}

function HighlightText({ text, query }) {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-primary/20 text-primary rounded px-0.5">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}
