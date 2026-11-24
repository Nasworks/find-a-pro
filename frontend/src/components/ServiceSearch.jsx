import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as LucideIcons from 'lucide-react';
import { Search, X, CalendarCheck, Sparkles } from 'lucide-react';
import { Button } from './ui/button';
import api from '../lib/api';

// Module-level cache so the two taxonomies are only fetched once per session.
let servicesCache = null;
let servicesPromise = null;

const loadServices = () => {
  if (servicesCache) return Promise.resolve(servicesCache);
  if (servicesPromise) return servicesPromise;
  servicesPromise = Promise.all([
    api.get('/services/taxonomy/residential').catch(() => ({ data: { categories: [] } })),
    api.get('/services/taxonomy/commercial').catch(() => ({ data: { categories: [] } })),
  ]).then(([res, com]) => {
    const byName = new Map();
    const add = (cats, type) => {
      (cats || []).forEach((c) => {
        (c.subcategories || []).forEach((s) => {
          const key = s.name.toLowerCase();
          const variant = {
            category_id: c.id, category_name: c.name, category_icon: c.icon, category_color: c.color,
            subcategory_id: s.id, subcategory_name: s.name,
          };
          const entry = byName.get(key) || { key, name: s.name, category_name: c.name, icon: c.icon, color: c.color };
          if (!entry[type]) entry[type] = variant;
          byName.set(key, entry);
        });
      });
    };
    add(res.data.categories, 'residential');
    add(com.data.categories, 'commercial');
    servicesCache = Array.from(byName.values());
    servicesPromise = null;
    return servicesCache;
  });
  return servicesPromise;
};

export const useAllServices = () => {
  const [services, setServices] = useState(servicesCache || []);
  useEffect(() => {
    let alive = true;
    loadServices().then((s) => { if (alive) setServices(s); });
    return () => { alive = false; };
  }, []);
  return services;
};

const scoreEntry = (entry, term, words) => {
  const name = entry.name.toLowerCase();
  const cat = entry.category_name.toLowerCase();
  if (name.startsWith(term)) return 100;
  if (name.split(/[\s&/,-]+/).some((w) => w.startsWith(term))) return 80;
  if (name.includes(term)) return 60;
  if (words.length > 1 && words.every((w) => name.includes(w) || cat.includes(w))) return 50;
  if (cat.includes(term)) return 30;
  return 0;
};

const Highlight = ({ text, query }) => {
  const idx = query ? text.toLowerCase().indexOf(query.toLowerCase()) : -1;
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <span className="text-primary font-semibold">{text.slice(idx, idx + query.length)}</span>
      {text.slice(idx + query.length)}
    </>
  );
};

/**
 * Search bar with predictive service suggestions + Book button.
 * Props: value, onChange(text), selected, onSelect(entry|null), onBook()
 */
export default function ServiceSearch({ value, onChange, selected, onSelect, onBook }) {
  const services = useAllServices();
  const [focused, setFocused] = useState(false);
  const [active, setActive] = useState(-1);
  const [detected, setDetected] = useState([]);
  const wrapRef = useRef(null);
  const term = value.trim().toLowerCase();

  // Keyword-based detection (e.g. "dripping tap" -> Tap & Toilet Repairs)
  useEffect(() => {
    if (term.length < 3) { setDetected([]); return undefined; }
    const id = setTimeout(() => {
      api.get('/services/detect', { params: { text: term, service_type: 'residential' } })
        .then((r) => {
          const list = [r.data.match, ...(r.data.alternatives || [])].filter(Boolean);
          setDetected(list.map((d) => d.subcategory_name.toLowerCase()));
        })
        .catch(() => setDetected([]));
    }, 250);
    return () => clearTimeout(id);
  }, [term]);

  const suggestions = useMemo(() => {
    if (term.length < 2) return [];
    const words = term.split(/\s+/).filter(Boolean);
    const scored = [];
    services.forEach((e) => {
      let s = scoreEntry(e, term, words);
      const d = detected.indexOf(e.key);
      if (d !== -1) s = Math.max(s, 95 - d);
      if (s > 0) scored.push({ e, s, detected: d !== -1 });
    });
    scored.sort((a, b) => b.s - a.s || a.e.name.localeCompare(b.e.name));
    return scored.slice(0, 8);
  }, [term, services, detected]);

  useEffect(() => { setActive(-1); }, [term]);

  useEffect(() => {
    const onDoc = (ev) => { if (wrapRef.current && !wrapRef.current.contains(ev.target)) setFocused(false); };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const showList = focused && suggestions.length > 0 && !(selected && selected.name === value);

  const choose = (entry) => {
    onChange(entry.name);
    onSelect(entry);
    setFocused(false);
  };

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown' && showList) { e.preventDefault(); setActive((a) => Math.min(a + 1, suggestions.length - 1)); }
    else if (e.key === 'ArrowUp' && showList) { e.preventDefault(); setActive((a) => Math.max(a - 1, -1)); }
    else if (e.key === 'Escape') setFocused(false);
    else if (e.key === 'Enter') {
      e.preventDefault();
      if (showList && active >= 0) choose(suggestions[active].e);
      else if (value.trim()) { setFocused(false); onBook(); }
    }
  };

  return (
    <div ref={wrapRef} className="relative w-full" data-testid="service-search">
      <div className={`flex items-center gap-2 p-2 pl-4 rounded-2xl bg-card border shadow-lg shadow-black/5 transition-colors ${focused ? 'border-primary/50 ring-4 ring-primary/10' : 'border-border'}`}>
        <Search className="w-5 h-5 text-muted-foreground shrink-0" />
        <input
          data-testid="service-search-input"
          value={value}
          onChange={(e) => { onChange(e.target.value); if (selected) onSelect(null); setFocused(true); }}
          onFocus={() => setFocused(true)}
          onKeyDown={onKeyDown}
          placeholder="What do you need done? e.g. leaking tap, heat pump"
          className="flex-1 min-w-0 h-11 bg-transparent outline-none text-base text-foreground placeholder:text-muted-foreground"
          autoComplete="off"
          role="combobox"
          aria-expanded={showList}
          aria-controls="service-search-list"
        />
        {value && (
          <button type="button" onClick={() => { onChange(''); onSelect(null); }} data-testid="service-search-clear" className="p-1.5 rounded-full text-muted-foreground hover:text-foreground hover:bg-accent" aria-label="Clear search">
            <X className="w-4 h-4" />
          </button>
        )}
        <Button data-testid="service-search-book" onClick={() => { setFocused(false); onBook(); }} disabled={!value.trim()} className="h-11 px-5 sm:px-6 rounded-xl text-base">
          <CalendarCheck className="w-4 h-4 mr-2" /> Book
        </Button>
      </div>

      {showList && (
        <ul id="service-search-list" role="listbox" data-testid="service-search-suggestions" className="absolute z-40 left-0 right-0 mt-2 py-1.5 bg-popover border border-border rounded-2xl shadow-xl max-h-[60vh] overflow-y-auto">
          {suggestions.map(({ e, detected: isDetected }, i) => {
            const Icon = LucideIcons[e.icon] || LucideIcons.Wrench;
            return (
              <li key={e.key} role="option" aria-selected={i === active}>
                <button
                  type="button"
                  data-testid={`service-suggestion-${(e.residential || e.commercial).subcategory_id}`}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => choose(e)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${i === active ? 'bg-accent' : ''}`}
                >
                  <span className="w-8 h-8 rounded-lg flex items-center justify-center text-white shrink-0" style={{ backgroundColor: e.color }}>
                    <Icon className="w-4 h-4" />
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="block text-sm text-foreground truncate"><Highlight text={e.name} query={term} /></span>
                    <span className="block text-xs text-muted-foreground truncate">{e.category_name}</span>
                  </span>
                  {isDetected && <Sparkles className="w-3.5 h-3.5 text-primary shrink-0" aria-label="Suggested" />}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
