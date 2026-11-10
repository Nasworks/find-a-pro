import React, { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Search, Star, Shield, ShieldCheck, Award, Loader2, X, MapPin, Sparkles, Users, Heart, LocateFixed, SlidersHorizontal } from 'lucide-react';
import { SidePane } from '../../components/SidePane';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Slider } from '../../components/ui/slider';
import ServicePicker from '../../components/ServicePicker';
import api from '../../lib/api';
import { toast } from 'sonner';

const RATE_BUCKETS = [
  { id: 'low', label: 'Low Rate', sub: 'Affordable', color: 'text-emerald-500 bg-emerald-500/10' },
  { id: 'medium', label: 'Medium Rate', sub: 'Good value', color: 'text-blue-500 bg-blue-500/10' },
  { id: 'high', label: 'High Rate', sub: 'Premium', color: 'text-amber-500 bg-amber-500/10' },
];

const RATING_LEVELS = ['any', '3', '3.5', '4', '4.5'];
const REVIEW_LEVELS = ['any', '5', '10', '25', '50'];
const JOB_LEVELS = ['any', '10', '25', '50', '100'];
const SORT_OPTIONS = [
  { id: 'best_match', label: 'Best Match' },
  { id: 'rating', label: 'Highest Rated' },
  { id: 'reviews', label: 'Most Reviews' },
  { id: 'price_asc', label: 'Price: Low to High' },
  { id: 'price_desc', label: 'Price: High to Low' },
  { id: 'nearest', label: 'Nearest First' },
];

const MAX_KM = 50;
const DEFAULT_ORIGIN = { lat: -36.8485, lng: 174.7633, label: 'Auckland CBD' };

const initialFilters = {
  category: '',
  category_name: '',
  subcategory: '',
  subcategory_name: '',
  min_rating: 'any',
  min_reviews: 'any',
  min_jobs: 'any',
  rate_bucket: '',
  verified_only: false,
  background_checked: false,
  accredited: false,
  max_km: MAX_KM,
  q: '',
  sort: 'best_match',
};

export default function FindProviders() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [filters, setFilters] = useState(() => ({
    ...initialFilters,
    category: searchParams.get('category') || '',
    subcategory: searchParams.get('subcategory') || '',
    category_name: searchParams.get('category_name') || '',
    subcategory_name: searchParams.get('subcategory_name') || '',
    q: searchParams.get('q') || '',
  }));
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [origin, setOrigin] = useState(DEFAULT_ORIGIN);
  const reqRef = useRef(0);

  const load = useCallback(() => {
    setLoading(true);
    const params = { sort: filters.sort, lat: origin.lat, lng: origin.lng };
    if (filters.max_km < MAX_KM) params.max_km = filters.max_km;
    if (filters.category) params.category = filters.category;
    if (filters.subcategory) params.subcategory = filters.subcategory;
    if (filters.q) params.q = filters.q;
    if (filters.min_rating !== 'any') params.min_rating = filters.min_rating;
    if (filters.min_reviews !== 'any') params.min_reviews = filters.min_reviews;
    if (filters.min_jobs !== 'any') params.min_jobs = filters.min_jobs;
    if (filters.rate_bucket) params.rate_bucket = filters.rate_bucket;
    if (filters.verified_only) params.verified_only = true;
    if (filters.background_checked) params.background_checked = true;
    if (filters.accredited) params.accredited = true;
    const reqId = ++reqRef.current;
    api.get('/providers/search', { params })
      .then((r) => { if (reqId === reqRef.current) setResults(r.data.results || []); })
      .catch(() => toast.error('Search failed'))
      .finally(() => { if (reqId === reqRef.current) setLoading(false); });
  }, [filters, origin]);

  useEffect(() => { load(); }, [load]);

  const set = (k, v) => setFilters((f) => ({ ...f, [k]: v }));
  const clearAll = () => setFilters(initialFilters);

  const activeChips = useMemo(() => {
    const chips = [];
    if (filters.category_name) chips.push({ k: 'category', label: filters.subcategory_name || filters.category_name });
    if (filters.rate_bucket) chips.push({ k: 'rate_bucket', label: RATE_BUCKETS.find((r) => r.id === filters.rate_bucket)?.label });
    if (filters.min_rating !== 'any') chips.push({ k: 'min_rating', label: `${filters.min_rating}★ and up` });
    if (filters.min_reviews !== 'any') chips.push({ k: 'min_reviews', label: `${filters.min_reviews}+ reviews` });
    if (filters.min_jobs !== 'any') chips.push({ k: 'min_jobs', label: `${filters.min_jobs}+ jobs` });
    if (filters.verified_only) chips.push({ k: 'verified_only', label: 'Verified' });
    if (filters.background_checked) chips.push({ k: 'background_checked', label: 'Background checked' });
    if (filters.accredited) chips.push({ k: 'accredited', label: 'Accredited' });
    if (filters.max_km < MAX_KM) chips.push({ k: 'max_km', label: `Within ${filters.max_km} km` });
    return chips;
  }, [filters]);

  const clearChip = (k) => {
    if (k === 'category') {
      setFilters((f) => ({ ...f, category: '', subcategory: '', category_name: '', subcategory_name: '' }));
    } else if (k === 'rate_bucket') {
      set('rate_bucket', '');
    } else if (k === 'verified_only') {
      set('verified_only', false);
    } else if (k === 'background_checked') {
      set('background_checked', false);
    } else if (k === 'max_km') {
      set('max_km', MAX_KM);
    } else if (k === 'accredited') {
      set('accredited', false);
    } else {
      set(k, 'any');
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-6" data-testid="find-providers-page">
      {/* Header */}
      <div className="mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-blue-600 text-white flex items-center justify-center shrink-0"><Users className="w-5 h-5" /></div>
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl md:text-3xl font-bold text-foreground">Find Providers</h1>
            <p className="text-sm text-muted-foreground">Browse verified pros — filter by service, rating, price, and credentials.</p>
          </div>
          <div className="shrink-0 whitespace-nowrap text-xs sm:text-sm px-2.5 py-1 rounded-full bg-muted text-muted-foreground self-start" data-testid="providers-count">{loading ? '…' : `${results.length} found`}</div>
        </div>
      </div>

      {/* Search bar */}
      <div className="flex flex-col md:flex-row gap-2 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            data-testid="providers-search"
            value={filters.q}
            onChange={(e) => set('q', e.target.value)}
            placeholder="Search by name, bio, or trade..."
            className="pl-9"
          />
        </div>
        <Button data-testid="providers-category-picker" variant="outline" onClick={() => setPickerOpen(true)}>
          <Sparkles className="w-4 h-4 mr-1.5" />
          {filters.category ? (filters.subcategory_name || filters.category_name) : 'Choose service'}
        </Button>
        <select
          data-testid="providers-sort"
          value={filters.sort}
          onChange={(e) => set('sort', e.target.value)}
          className="rounded-md border border-border bg-card text-foreground px-3 py-2 text-sm h-10"
        >
          {SORT_OPTIONS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
      </div>

      {/* Active filter chips */}
      {activeChips.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {activeChips.map((c) => (
            <button key={c.k} onClick={() => clearChip(c.k)} className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium hover:bg-primary/20 transition-colors">
              {c.label} <X className="w-3 h-3" />
            </button>
          ))}
          <button onClick={clearAll} className="text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded-full">Clear all</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-6">
        <SidePane label="Filters" title="Filter providers" icon={SlidersHorizontal} side="left" testid="filters-pane">
          <FiltersPanel filters={filters} set={set} origin={origin} setOrigin={setOrigin} />
        </SidePane>

        <div>
          {loading ? (
            <div className="py-16 flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
          ) : results.length === 0 ? (
            <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
              <Search className="w-8 h-8 mx-auto text-muted-foreground opacity-40 mb-2" />
              <div className="font-medium text-foreground">No providers match your filters</div>
              <p className="text-sm text-muted-foreground mt-1">Try loosening a filter or picking a different category.</p>
              <Button onClick={clearAll} className="mt-4" variant="outline">Clear filters</Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {results.map((p) => (
                <ProviderCard
                  key={p.user_id}
                  p={p}
                  onClick={() => navigate(`/providers/${p.user_id}`)}
                  onToggleSave={(next) => setResults((rs) => rs.map((r) => r.user_id === p.user_id ? { ...r, is_saved: next } : r))}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <ServicePicker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        serviceType="residential"
        value={filters.category ? { category_id: filters.category, subcategory_id: filters.subcategory } : undefined}
        onSelect={(sel) => setFilters((f) => ({
          ...f,
          category: sel.category_id,
          category_name: sel.category_name,
          subcategory: sel.subcategory_id,
          subcategory_name: sel.subcategory_name,
        }))}
      />
    </div>
  );
}

function FiltersPanel({ filters, set, origin, setOrigin }) {
  return (
    <aside className="space-y-4">
      <DistanceFilter value={filters.max_km} onCommit={(v) => set('max_km', v)} origin={origin} setOrigin={setOrigin} />

      {/* Provider Rate */}
      <Card title="Provider Rate">
        <div className="grid grid-cols-3 gap-2">
          {RATE_BUCKETS.map((b) => (
            <button
              key={b.id}
              data-testid={`filter-rate-${b.id}`}
              onClick={() => set('rate_bucket', filters.rate_bucket === b.id ? '' : b.id)}
              className={`text-center p-2.5 rounded-xl border-2 transition-all ${filters.rate_bucket === b.id ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}
            >
              <div className={`w-8 h-8 rounded-full ${b.color} flex items-center justify-center mx-auto mb-1`}>
                {b.id === 'low' ? '$' : b.id === 'medium' ? <Award className="w-3.5 h-3.5" /> : <Star className="w-3.5 h-3.5" />}
              </div>
              <div className="text-[11px] font-semibold text-foreground leading-tight">{b.label}</div>
              <div className="text-[10px] text-muted-foreground">{b.sub}</div>
            </button>
          ))}
        </div>
      </Card>

      <PillGroup label="Provider Rating" name="min_rating" levels={RATING_LEVELS} value={filters.min_rating} onChange={(v) => set('min_rating', v)} suffix="+" />
      <PillGroup label="Minimum Reviews" name="min_reviews" levels={REVIEW_LEVELS} value={filters.min_reviews} onChange={(v) => set('min_reviews', v)} suffix="+" />
      <PillGroup label="Completed Jobs" name="min_jobs" levels={JOB_LEVELS} value={filters.min_jobs} onChange={(v) => set('min_jobs', v)} suffix="+" />

      <Card title="Trust & Safety">
        <div className="space-y-2">
          <ToggleRow icon={ShieldCheck} label="Background Checked" sub="Criminal record verified" checked={filters.background_checked} onChange={(v) => set('background_checked', v)} testId="filter-bg-checked" />
          <ToggleRow icon={Shield} label="Verified Provider" sub="ID & business verified" checked={filters.verified_only} onChange={(v) => set('verified_only', v)} testId="filter-verified" />
          <ToggleRow icon={Award} label="Accreditation Verified" sub="Trade qualifications confirmed" checked={filters.accredited} onChange={(v) => set('accredited', v)} testId="filter-accredited" />
        </div>
      </Card>
    </aside>
  );
}

function DistanceFilter({ value, onCommit, origin, setOrigin }) {
  const [local, setLocal] = useState(value);
  const [locating, setLocating] = useState(false);
  useEffect(() => setLocal(value), [value]);
  const useMyLocation = () => {
    if (!navigator.geolocation) return toast.error('Location is not available in this browser');
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (p) => { setOrigin({ lat: p.coords.latitude, lng: p.coords.longitude, label: 'Your location' }); setLocating(false); },
      () => { toast.error('Could not get your location'); setLocating(false); },
      { timeout: 8000 },
    );
  };
  return (
    <Card title="Distance Away">
      <div className="flex items-baseline justify-between mb-3">
        <span className="text-2xl font-bold text-foreground tabular-nums" data-testid="distance-value">{local >= MAX_KM ? 'Any' : `${local} km`}</span>
        <span className="text-[11px] text-muted-foreground">{local >= MAX_KM ? 'no limit' : 'or closer'}</span>
      </div>
      <Slider
        data-testid="distance-slider"
        min={1}
        max={MAX_KM}
        step={1}
        value={[local]}
        onValueChange={([v]) => setLocal(v)}
        onValueCommit={([v]) => onCommit(v)}
      />
      <div className="flex justify-between text-[10px] text-muted-foreground mt-1.5"><span>1 km</span><span>25 km</span><span>{MAX_KM}+ km</span></div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-x-2 gap-y-1 text-xs">
        <span className="inline-flex items-center gap-1 text-muted-foreground" data-testid="distance-origin"><MapPin className="w-3 h-3 text-primary" /> From {origin.label}</span>
        {origin.label === DEFAULT_ORIGIN.label ? (
          <button data-testid="use-my-location" onClick={useMyLocation} disabled={locating} className="inline-flex items-center gap-1 text-primary hover:underline shrink-0">
            {locating ? <Loader2 className="w-3 h-3 animate-spin" /> : <LocateFixed className="w-3 h-3" />} Use my location
          </button>
        ) : (
          <button data-testid="reset-location" onClick={() => setOrigin(DEFAULT_ORIGIN)} className="text-muted-foreground hover:text-foreground shrink-0">Reset</button>
        )}
      </div>
    </Card>
  );
}

function Card({ title, children }) {
  return (
    <div className="bg-card border border-border rounded-2xl p-4">
      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">{title}</div>
      {children}
    </div>
  );
}

function PillGroup({ label, name, levels, value, onChange, suffix }) {
  return (
    <Card title={label}>
      <div className="flex flex-wrap gap-1.5">
        {levels.map((lv) => (
          <button
            key={lv}
            data-testid={`filter-${name}-${lv}`}
            onClick={() => onChange(lv)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${value === lv ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent hover:text-foreground'}`}
          >
            {lv === 'any' ? 'Any' : `${lv}${suffix}`}
          </button>
        ))}
      </div>
    </Card>
  );
}

function ToggleRow({ icon: Icon, label, sub, checked, onChange, testId }) {
  return (
    <label className="flex items-center gap-2.5 cursor-pointer">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${checked ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-foreground">{label}</div>
        <div className="text-[11px] text-muted-foreground">{sub}</div>
      </div>
      <input data-testid={testId} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="w-9 h-5 accent-primary" />
    </label>
  );
}

const AVATAR_COLORS = ['bg-emerald-500', 'bg-blue-500', 'bg-violet-500', 'bg-amber-500', 'bg-rose-500', 'bg-teal-500', 'bg-orange-500'];

function ProviderCard({ p, onClick, onToggleSave }) {
  const initials = (p.business_name || 'P').split(' ').slice(0, 2).map((s) => s[0]).join('').toUpperCase();
  const avatarColor = AVATAR_COLORS[(p.user_id || '').charCodeAt(0) % AVATAR_COLORS.length];
  const [busy, setBusy] = useState(false);
  const toggleSave = async (e) => {
    e.stopPropagation();
    if (busy) return;
    setBusy(true);
    const next = !p.is_saved;
    onToggleSave?.(next);
    try {
      if (next) {
        await api.post(`/saved-providers/${p.user_id}`);
        toast.success(`Saved ${p.business_name}`);
      } else {
        await api.delete(`/saved-providers/${p.user_id}`);
        toast.success('Removed from Saved Pros');
      }
    } catch {
      onToggleSave?.(!next);
      toast.error('Could not update Saved Pros');
    } finally {
      setBusy(false);
    }
  };
  return (
    <div
      data-testid={`provider-card-${p.user_id}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick(); }}
      className="relative text-left bg-card border border-border rounded-2xl p-4 hover:border-primary/40 hover:shadow-md hover:shadow-primary/5 transition-all group cursor-pointer"
    >
      <button
        data-testid={`save-toggle-${p.user_id}`}
        onClick={toggleSave}
        aria-pressed={!!p.is_saved}
        aria-label={p.is_saved ? 'Remove from Saved Pros' : 'Add to Saved Pros'}
        className={`absolute top-3 right-3 w-8 h-8 rounded-full flex items-center justify-center transition-colors ${p.is_saved ? 'bg-rose-500/15 text-rose-500 hover:bg-rose-500/25' : 'bg-muted text-muted-foreground hover:bg-accent hover:text-foreground'}`}
      >
        <Heart className={`w-4 h-4 ${p.is_saved ? 'fill-rose-500' : ''}`} />
      </button>
      <div className="flex items-start gap-3 pr-8">
        <div className={`w-12 h-12 rounded-full ${avatarColor} text-white font-bold flex items-center justify-center relative shrink-0`}>
          {initials}
          {p.verified && (
            <span className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-primary text-white border-2 border-card flex items-center justify-center">
              <Shield className="w-2 h-2" />
            </span>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-1">
            <div className="font-semibold text-foreground truncate group-hover:text-primary transition-colors">{p.business_name}</div>
            <div className="flex items-center gap-0.5 text-xs font-bold text-amber-500 shrink-0">
              <Star className="w-3.5 h-3.5 fill-amber-500" /> {p.rating?.toFixed?.(1) ?? '—'}
            </div>
          </div>
          <div className="text-xs text-muted-foreground truncate">{p.categories?.join(', ')}</div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-1">
        {p.verified && <Badge className="text-[10px] bg-blue-500/10 text-blue-600 border-transparent">ID</Badge>}
        {p.insured && <Badge className="text-[10px] bg-emerald-500/10 text-emerald-600 border-transparent">Insured</Badge>}
        {p.background_checked && <Badge className="text-[10px] bg-amber-500/10 text-amber-600 border-transparent">BG Check</Badge>}
        {p.accredited && <Badge className="text-[10px] bg-violet-500/10 text-violet-600 border-transparent">Accredited</Badge>}
      </div>
      <p className="mt-3 text-xs text-muted-foreground line-clamp-2">{p.bio}</p>
      <div className="mt-3 pt-3 border-t border-border flex items-center justify-between text-xs">
        <span className="inline-flex items-center gap-1 text-muted-foreground" data-testid={`provider-distance-${p.user_id}`}><MapPin className="w-3 h-3" /> {p.distance_km != null ? `${p.distance_km} km away` : 'Auckland'}</span>
        <span className="font-bold text-foreground">${p.hourly_rate?.toFixed?.(0)}/hr</span>
      </div>
    </div>
  );
}
