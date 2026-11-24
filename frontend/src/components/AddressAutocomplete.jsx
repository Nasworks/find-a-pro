import React, { useEffect, useRef, useState } from 'react';
import { MapPin, Loader2, X } from 'lucide-react';
import api from '../lib/api';

const newSession = () => (window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random()}`);

/**
 * Address input with suggestions as you type (Google when configured, otherwise free map search).
 * Props: value, onChange(text), onSelect({ address, lat, lng }), placeholder, testid, autoFocus
 */
export default function AddressAutocomplete({ value, onChange, onSelect, placeholder = 'Start typing an address…', testid = 'address-input', autoFocus = false }) {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [source, setSource] = useState('');
  const sessionRef = useRef(newSession());
  const skipRef = useRef(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (skipRef.current) { skipRef.current = false; return undefined; }
    const q = (value || '').trim();
    if (q.length < 3) { setResults([]); setLoading(false); return undefined; }
    setLoading(true);
    const id = setTimeout(() => {
      api.get('/address/search', { params: { q, session: sessionRef.current } })
        .then((r) => { setResults(r.data.results || []); setSource(r.data.source); setActive(-1); })
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, 300);
    return () => clearTimeout(id);
  }, [value]);

  useEffect(() => {
    const onDoc = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const choose = async (r) => {
    setOpen(false);
    skipRef.current = true;
    let picked = { address: r.address, lat: r.lat, lng: r.lng };
    if (r.lat == null && r.id?.startsWith('g:')) {
      try {
        const d = await api.get('/address/details', { params: { place_id: r.id, session: sessionRef.current } });
        picked = { address: d.data.address || r.address, lat: d.data.lat, lng: d.data.lng };
      } catch { /* keep the text address */ }
    }
    sessionRef.current = newSession();
    onChange(picked.address);
    onSelect?.(picked);
    setResults([]);
  };

  const onKeyDown = (e) => {
    if (!open || !results.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, results.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    else if (e.key === 'Enter' && active >= 0) { e.preventDefault(); choose(results[active]); }
    else if (e.key === 'Escape') setOpen(false);
  };

  const showList = open && (value || '').trim().length >= 3 && (results.length > 0 || !loading);

  return (
    <div ref={wrapRef} className="relative">
      <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
      <input
        data-testid={testid}
        value={value}
        onChange={(e) => { onChange(e.target.value); onSelect?.(null); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        autoFocus={autoFocus}
        autoComplete="off"
        className="flex h-10 w-full rounded-md border border-input bg-transparent pl-9 pr-9 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      />
      <span className="absolute right-3 top-1/2 -translate-y-1/2">
        {loading ? <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /> : value ? (
          <button type="button" onClick={() => { onChange(''); onSelect?.(null); }} className="text-muted-foreground hover:text-foreground" aria-label="Clear address"><X className="w-4 h-4" /></button>
        ) : null}
      </span>
      {showList && (
        <ul className="absolute z-50 left-0 right-0 mt-1.5 py-1 bg-popover border border-border rounded-xl shadow-xl max-h-72 overflow-y-auto" data-testid={`${testid}-suggestions`}>
          {results.length === 0 ? (
            <li className="px-3 py-2.5 text-xs text-muted-foreground">No matching addresses — you can keep what you typed.</li>
          ) : results.map((r, i) => (
            <li key={r.id}>
              <button
                type="button"
                data-testid={`${testid}-option-${i}`}
                onMouseMove={() => active !== i && setActive(i)}
                onClick={() => choose(r)}
                className={`w-full flex items-start gap-2.5 px-3 py-2 text-left ${i === active ? 'bg-accent' : ''}`}
              >
                <MapPin className="w-4 h-4 mt-0.5 text-primary shrink-0" />
                <span className="min-w-0">
                  <span className="block text-sm text-foreground truncate">{r.main}</span>
                  {r.secondary && <span className="block text-xs text-muted-foreground truncate">{r.secondary}</span>}
                </span>
              </button>
            </li>
          ))}
          {source === 'osm' && results.length > 0 && (
            <li className="px-3 pt-1 pb-1.5 text-[10px] text-muted-foreground text-right">Addresses © OpenStreetMap</li>
          )}
        </ul>
      )}
    </div>
  );
}
