import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as LucideIcons from 'lucide-react';
import {
  ArrowLeft, ArrowRight, Check, Loader2, Search, User, Users, Building2, Home as HomeIcon, X, ChevronDown, Tag, Clock, ClipboardList,
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import api from '../../lib/api';
import { toast } from 'sonner';
import { useViewMode } from '../../context/ViewModeContext';

const SIZES = [
  { v: 'solo', l: 'Solo operator', d: 'Just me on the tools', icon: User },
  { v: 'small_team', l: 'Small team', d: '2–5 people', icon: Users },
  { v: 'medium_enterprise', l: 'Medium business', d: 'Deployable technicians & crews', icon: Building2 },
];
const TRACKS = [
  { v: 'residential', l: 'Residential', d: 'Homes, rentals, apartments', icon: HomeIcon },
  { v: 'commercial', l: 'Commercial', d: 'Offices, retail, industrial', icon: Building2 },
];
const MODES = [
  { v: 'small_fixed', l: 'Small & fixed-cost tasks', icon: Tag },
  { v: 'hourly', l: 'Larger & hourly-based jobs', icon: Clock },
  { v: 'large_quote', l: 'Larger fixed-cost projects (custom quote)', icon: ClipboardList },
];
const STEPS = ['Business details', 'Specializations', 'Pricing & job sizes'];
const keyOf = (t, c, s) => `${t}|${c}|${s}`;

export default function ProviderOnboarding() {
  const navigate = useNavigate();
  const { compact } = useViewMode();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [biz, setBiz] = useState({ business_name: '', business_size: '', service_tracks: ['residential'], service_area_suburbs: [], bio: '' });
  const [suburbInput, setSuburbInput] = useState('');
  const [taxonomy, setTaxonomy] = useState({ residential: [], commercial: [] });
  const [selected, setSelected] = useState({}); // key -> spec
  const [tab, setTab] = useState('residential');
  const [query, setQuery] = useState('');
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    Promise.all([
      api.get('/providers/me/onboarding'),
      api.get('/services/taxonomy/residential'),
      api.get('/services/taxonomy/commercial'),
    ]).then(([o, r, c]) => {
      const p = o.data.profile || {};
      setEditing(!!o.data.onboarded);
      setBiz({
        business_name: p.business_name || '',
        business_size: p.business_size || '',
        service_tracks: p.service_tracks?.length ? p.service_tracks : ['residential'],
        service_area_suburbs: p.service_area_suburbs || [],
        bio: p.bio || '',
      });
      const sel = {};
      (o.data.specializations || []).forEach((s) => { sel[keyOf(s.service_type, s.category_id, s.subcategory_id)] = s; });
      setSelected(sel);
      setTaxonomy({ residential: r.data.categories || [], commercial: c.data.categories || [] });
    }).catch(() => toast.error('Could not load your details')).finally(() => setLoading(false));
  }, []);

  useEffect(() => { if (!biz.service_tracks.includes(tab)) setTab(biz.service_tracks[0] || 'residential'); }, [biz.service_tracks, tab]);

  const toggleTrack = (t) => setBiz((b) => {
    const has = b.service_tracks.includes(t);
    const next = has ? b.service_tracks.filter((x) => x !== t) : [...b.service_tracks, t];
    return { ...b, service_tracks: next.length ? next : b.service_tracks };
  });
  const addSuburb = () => {
    const v = suburbInput.trim();
    if (!v) return;
    setBiz((b) => (b.service_area_suburbs.some((x) => x.toLowerCase() === v.toLowerCase()) ? b : { ...b, service_area_suburbs: [...b.service_area_suburbs, v] }));
    setSuburbInput('');
  };

  const toggleSub = (t, cat, sub) => setSelected((s) => {
    const k = keyOf(t, cat.id, sub.id);
    const n = { ...s };
    if (n[k]) delete n[k];
    else n[k] = { service_type: t, category_id: cat.id, category_name: cat.name, subcategory_id: sub.id, subcategory_name: sub.name, pricing_modes: ['small_fixed', 'hourly', 'large_quote'], rate: null };
    return n;
  });
  const toggleCat = (t, cat) => setSelected((s) => {
    const n = { ...s };
    const all = cat.subcategories.every((sub) => n[keyOf(t, cat.id, sub.id)]);
    cat.subcategories.forEach((sub) => {
      const k = keyOf(t, cat.id, sub.id);
      if (all) delete n[k];
      else if (!n[k]) n[k] = { service_type: t, category_id: cat.id, category_name: cat.name, subcategory_id: sub.id, subcategory_name: sub.name, pricing_modes: ['small_fixed', 'hourly', 'large_quote'], rate: null };
    });
    return n;
  });

  // Only keep specializations for tracks the provider still serves
  const activeSpecs = useMemo(() => Object.entries(selected).filter(([, v]) => biz.service_tracks.includes(v.service_type)), [selected, biz.service_tracks]);

  const filteredCats = useMemo(() => {
    const q = query.trim().toLowerCase();
    const cats = taxonomy[tab] || [];
    if (!q) return cats;
    return cats.map((c) => (c.name.toLowerCase().includes(q) ? c : { ...c, subcategories: c.subcategories.filter((s) => s.name.toLowerCase().includes(q)) }))
      .filter((c) => c.subcategories.length);
  }, [taxonomy, tab, query]);

  const setModes = (k, mode) => setSelected((s) => {
    const cur = s[k].pricing_modes;
    const next = cur.includes(mode) ? cur.filter((m) => m !== mode) : [...cur, mode];
    return { ...s, [k]: { ...s[k], pricing_modes: next } };
  });
  const setAllModes = (mode, on) => setSelected((s) => {
    const n = { ...s };
    activeSpecs.forEach(([k]) => {
      const cur = n[k].pricing_modes;
      n[k] = { ...n[k], pricing_modes: on ? Array.from(new Set([...cur, mode])) : cur.filter((m) => m !== mode) };
    });
    return n;
  });
  const setRate = (k, v) => setSelected((s) => ({ ...s, [k]: { ...s[k], rate: v } }));

  const canNext = step === 0
    ? biz.business_name.trim() && biz.business_size && biz.service_tracks.length
    : step === 1 ? activeSpecs.length > 0 : activeSpecs.every(([, v]) => v.pricing_modes.length > 0);

  const next = () => {
    if (!canNext) {
      toast.error(step === 0 ? 'Add your business name, size and who you serve' : step === 1 ? 'Select at least one category and subcategory' : 'Each specialization needs at least one job size');
      return;
    }
    if (step < 2) { setStep(step + 1); window.scrollTo({ top: 0 }); return; }
    save();
  };

  const save = async () => {
    setSaving(true);
    try {
      await api.put('/providers/me/onboarding', {
        ...biz,
        specializations: activeSpecs.map(([, v]) => ({
          service_type: v.service_type, category_id: v.category_id, subcategory_id: v.subcategory_id,
          pricing_modes: v.pricing_modes, rate: v.rate === '' || v.rate == null ? null : Number(v.rate),
        })),
      });
      toast.success(editing ? 'Specializations updated' : 'You\'re all set — matched jobs will appear on your dashboard');
      window.scrollTo({ top: 0 });
      navigate('/provider/dashboard');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not save');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-10 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>;

  const grouped = activeSpecs.reduce((acc, [k, v]) => {
    const g = `${v.service_type}|${v.category_name}`;
    (acc[g] = acc[g] || []).push([k, v]);
    return acc;
  }, {});

  return (
    <div className="max-w-3xl mx-auto p-4 sm:p-6" data-testid="provider-onboarding">
      <div className="mb-6">
        <div className="text-xs font-semibold uppercase tracking-wider text-primary">{editing ? 'Edit your services' : 'Provider onboarding'}</div>
        <h1 className="text-2xl sm:text-3xl font-bold text-foreground mt-1">{STEPS[step]}</h1>
        <div className="flex gap-2 mt-4" data-testid="onboarding-progress">
          {STEPS.map((s, i) => (
            <button key={s} type="button" onClick={() => i < step && setStep(i)} className="flex-1 text-left" disabled={i > step}>
              <div className={`h-1.5 rounded-full ${i <= step ? 'bg-primary' : 'bg-muted'}`} />
              <div className={`text-[11px] mt-1.5 ${i === step ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>{i + 1}. {s}</div>
            </button>
          ))}
        </div>
      </div>

      {step === 0 && (
        <div className="space-y-6">
          <div>
            <Label>Business name</Label>
            <Input data-testid="onboarding-business-name" value={biz.business_name} onChange={(e) => setBiz({ ...biz, business_name: e.target.value })} placeholder="e.g. Kiwi Plumbing Ltd" className="mt-1.5" maxLength={80} />
          </div>
          <div>
            <Label>Business size</Label>
            <div className="grid sm:grid-cols-3 gap-2 mt-1.5">
              {SIZES.map(({ v, l, d, icon: Icon }) => (
                <button key={v} type="button" data-testid={`onboarding-size-${v}`} onClick={() => setBiz({ ...biz, business_size: v })}
                  className={`p-3.5 rounded-xl border-2 text-left transition-colors ${biz.business_size === v ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}>
                  <Icon className={`w-5 h-5 mb-1.5 ${biz.business_size === v ? 'text-primary' : 'text-muted-foreground'}`} />
                  <div className="text-sm font-semibold text-foreground">{l}</div>
                  <div className="text-xs text-muted-foreground">{d}</div>
                </button>
              ))}
            </div>
          </div>
          <div>
            <Label>Who do you serve? <span className="text-muted-foreground font-normal">(pick one or both)</span></Label>
            <div className="grid grid-cols-2 gap-2 mt-1.5">
              {TRACKS.map(({ v, l, d, icon: Icon }) => {
                const on = biz.service_tracks.includes(v);
                return (
                  <button key={v} type="button" data-testid={`onboarding-track-${v}`} aria-pressed={on} onClick={() => toggleTrack(v)}
                    className={`relative p-3.5 rounded-xl border-2 text-left transition-colors ${on ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}>
                    {on && <Check className="absolute top-3 right-3 w-4 h-4 text-primary" />}
                    <Icon className={`w-5 h-5 mb-1.5 ${on ? 'text-primary' : 'text-muted-foreground'}`} />
                    <div className="text-sm font-semibold text-foreground">{l}</div>
                    <div className="text-xs text-muted-foreground">{d}</div>
                  </button>
                );
              })}
            </div>
          </div>
          <div>
            <Label>Service suburbs <span className="text-muted-foreground font-normal">(leave empty to cover your whole service radius)</span></Label>
            <div className="flex gap-2 mt-1.5">
              <Input data-testid="onboarding-suburb-input" value={suburbInput} onChange={(e) => setSuburbInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addSuburb(); } }} placeholder="e.g. Ponsonby — press Enter to add" />
              <Button type="button" variant="outline" onClick={addSuburb} data-testid="onboarding-suburb-add">Add</Button>
            </div>
            {biz.service_area_suburbs.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {biz.service_area_suburbs.map((sb) => (
                  <span key={sb} className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs text-foreground">
                    {sb}
                    <button type="button" aria-label={`Remove ${sb}`} onClick={() => setBiz((b) => ({ ...b, service_area_suburbs: b.service_area_suburbs.filter((x) => x !== sb) }))}><X className="w-3 h-3" /></button>
                  </span>
                ))}
              </div>
            )}
          </div>
          <div>
            <Label>About your business <span className="text-muted-foreground font-normal">(optional)</span></Label>
            <Textarea value={biz.bio} onChange={(e) => setBiz({ ...biz, bio: e.target.value })} rows={3} className="mt-1.5" maxLength={600} placeholder="Qualifications, years in business, what you're known for…" />
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">Choose every service you're qualified to do. You'll only be matched with jobs in these subcategories.</p>
          {biz.service_tracks.length > 1 && (
            <div className="inline-flex rounded-xl bg-muted p-1">
              {biz.service_tracks.map((t) => (
                <button key={t} type="button" data-testid={`onboarding-tab-${t}`} onClick={() => setTab(t)}
                  className={`px-4 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors ${tab === t ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground'}`}>
                  {t} <span className="text-xs opacity-70">({activeSpecs.filter(([, v]) => v.service_type === t).length})</span>
                </button>
              ))}
            </div>
          )}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input data-testid="onboarding-spec-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search services — e.g. hot water, LED, gutter" className="pl-9" />
          </div>
          <div className="space-y-2">
            {filteredCats.map((cat) => {
              const Icon = LucideIcons[cat.icon] || LucideIcons.Wrench;
              const count = cat.subcategories.filter((s) => selected[keyOf(tab, cat.id, s.id)]).length;
              const allOn = count === cat.subcategories.length && count > 0;
              const isOpen = expanded[`${tab}|${cat.id}`] || !!query.trim();
              return (
                <div key={cat.id} className="border border-border rounded-xl bg-card overflow-hidden" data-testid={`onboarding-cat-${tab}-${cat.id}`}>
                  <div className="flex items-center gap-3 p-3">
                    <button type="button" onClick={() => toggleCat(tab, cat)} aria-label={`Select all ${cat.name}`} data-testid={`onboarding-cat-all-${tab}-${cat.id}`}
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 ${allOn ? 'bg-primary border-primary' : count ? 'border-primary' : 'border-border'}`}>
                      {allOn ? <Check className="w-3 h-3 text-primary-foreground" /> : count ? <span className="w-2 h-0.5 bg-primary" /> : null}
                    </button>
                    <button type="button" onClick={() => setExpanded((e) => ({ ...e, [`${tab}|${cat.id}`]: !isOpen }))} className="flex-1 flex items-center gap-3 text-left min-w-0" data-testid={`onboarding-cat-toggle-${tab}-${cat.id}`}>
                      <span className="w-8 h-8 rounded-lg flex items-center justify-center text-white shrink-0" style={{ backgroundColor: cat.color }}><Icon className="w-4 h-4" /></span>
                      <span className="flex-1 min-w-0">
                        <span className="block text-sm font-semibold text-foreground truncate">{cat.name}</span>
                        <span className="block text-xs text-muted-foreground">{count ? `${count} of ${cat.subcategories.length} selected` : `${cat.subcategories.length} services`}</span>
                      </span>
                      <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                    </button>
                  </div>
                  {isOpen && (
                    <div className="px-3 pb-3 grid sm:grid-cols-2 gap-1.5">
                      {cat.subcategories.map((sub) => {
                        const on = !!selected[keyOf(tab, cat.id, sub.id)];
                        return (
                          <button key={sub.id} type="button" onClick={() => toggleSub(tab, cat, sub)} data-testid={`onboarding-sub-${tab}-${cat.id}-${sub.id}`} aria-pressed={on}
                            className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-left text-sm transition-colors ${on ? 'border-primary bg-primary/5 text-foreground' : 'border-border text-muted-foreground hover:border-primary/40'}`}>
                            <span className={`w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 ${on ? 'bg-primary border-primary' : 'border-border'}`}>{on && <Check className="w-2.5 h-2.5 text-primary-foreground" />}</span>
                            <span className="truncate">{sub.name}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
            {filteredCats.length === 0 && <div className="text-sm text-muted-foreground text-center py-8">No services match “{query}”</div>}
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">Choose which job sizes you take for each service. You'll only be matched with jobs of those sizes.</p>
          <div className="bg-card border border-border rounded-xl p-3">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Apply to all</div>
            <div className="flex flex-wrap gap-2">
              {MODES.map(({ v, l }) => {
                const allOn = activeSpecs.every(([, s]) => s.pricing_modes.includes(v));
                return (
                  <button key={v} type="button" data-testid={`onboarding-all-${v}`} onClick={() => setAllModes(v, !allOn)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${allOn ? 'bg-primary text-primary-foreground border-primary' : 'border-border text-muted-foreground hover:border-primary/40'}`}>
                    {allOn ? '✓ ' : ''}{l}
                  </button>
                );
              })}
            </div>
          </div>
          {Object.entries(grouped).map(([g, items]) => {
            const [t, catName] = g.split('|');
            return (
              <div key={g} className="bg-card border border-border rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  {t === 'commercial' ? <Building2 className="w-4 h-4 text-blue-500" /> : <HomeIcon className="w-4 h-4 text-emerald-500" />}
                  <span className="font-semibold text-foreground text-sm">{catName}</span>
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{t}</span>
                </div>
                <div className="space-y-3">
                  {items.map(([k, v]) => (
                    <div key={k} className="border-t border-border/60 pt-3 first:border-0 first:pt-0" data-testid={`onboarding-pricing-${v.service_type}-${v.subcategory_id}`}>
                      <div className="flex items-center justify-between gap-3 flex-wrap">
                        <div className="text-sm font-medium text-foreground">{v.subcategory_name}</div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs text-muted-foreground">Rate $</span>
                          <Input type="number" min="1" value={v.rate ?? ''} onChange={(e) => setRate(k, e.target.value)} placeholder="/hr or base" className="h-8 w-28 text-sm" data-testid={`onboarding-rate-${v.service_type}-${v.subcategory_id}`} />
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {MODES.map(({ v: m, l, icon: Icon }) => {
                          const on = v.pricing_modes.includes(m);
                          return (
                            <button key={m} type="button" onClick={() => setModes(k, m)} aria-pressed={on} data-testid={`onboarding-mode-${v.service_type}-${v.subcategory_id}-${m}`}
                              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs border transition-colors ${on ? 'border-primary bg-primary/10 text-foreground' : 'border-border text-muted-foreground'}`}>
                              <Icon className="w-3 h-3" /> {l}
                            </button>
                          );
                        })}
                      </div>
                      {v.pricing_modes.length === 0 && <div className="text-xs text-destructive mt-1">Pick at least one job size</div>}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="sticky z-30 -mx-4 sm:-mx-6 mt-8 bg-background/95 backdrop-blur border-t border-border" style={{ bottom: compact ? 64 : 0 }}>
        <div className="px-4 sm:px-6 py-3 flex items-center gap-3">
          {step > 0 ? (
            <Button variant="outline" onClick={() => setStep(step - 1)} data-testid="onboarding-back"><ArrowLeft className="w-4 h-4 mr-1" /> Back</Button>
          ) : editing ? (
            <Button variant="outline" onClick={() => navigate(-1)}>Cancel</Button>
          ) : <span />}
          <div className="flex-1 text-xs text-muted-foreground text-center" data-testid="onboarding-selected-count">
            {activeSpecs.length} specialization{activeSpecs.length === 1 ? '' : 's'} selected
          </div>
          <Button onClick={next} disabled={saving} data-testid="onboarding-next">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : step < 2 ? <>Next <ArrowRight className="w-4 h-4 ml-1" /></> : <>{editing ? 'Save changes' : 'Finish'} <Check className="w-4 h-4 ml-1" /></>}
          </Button>
        </div>
      </div>
    </div>
  );
}
