import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import * as LucideIcons from 'lucide-react';
import {
  Loader2, Home as HomeIcon, Building2, ChevronRight, Sparkles, Layers, KeyRound, ShieldCheck,
  Pencil, Users, ClipboardList, Check, ArrowRight, ArrowLeft, Tag, Clock, CalendarDays,
} from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { RadioGroup, RadioGroupItem } from './ui/radio-group';
import { Sheet, SheetContent, SheetTitle, SheetDescription } from './ui/sheet';
import { Badge } from './ui/badge';
import ServicePicker from './ServicePicker';
import { useServiceDetect, DetectedAlternatives, providersLink } from './ServiceDetect';
import { MediaUploader } from './MediaUploader';
import JobLocationPicker from './JobLocationPicker';
import { PROPERTY_ROLES } from './MyPropertiesCard';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';
import { toast } from 'sonner';

// Roles that default to commercial when they hit Post-a-Job
const COMMERCIAL_DEFAULT_ROLES = new Set(['facilities', 'property']);

const EMPTY_SERVICE = {
  category: '', category_name: '', category_icon: '', category_color: '', subcategory: '', subcategory_name: '',
};
const serviceFields = (sel) => ({
  category: sel.category_id,
  category_name: sel.category_name,
  category_icon: sel.category_icon,
  category_color: sel.category_color,
  subcategory: sel.subcategory_id,
  subcategory_name: sel.subcategory_name,
});

// Every job is posted open: any matching pro can quote or bid, with no cap on replies.
const OPEN_MODE = 'bids';

// Job size / pricing structure — drives which specialised pros get matched.
export const JOB_SIZES = [
  { v: 'small_fixed', l: 'Small Fixed-Cost Job', short: 'Small fixed price', icon: Tag, iconCls: 'bg-emerald-500', d: 'Quick tasks at a set price · Matched pros accept & you choose' },
  { v: 'hourly', l: 'Hourly Job', short: 'Hourly', icon: Clock, iconCls: 'bg-blue-500', d: 'Larger jobs billed by the hour · Give an estimate of the hours' },
  { v: 'large_quote', l: 'Large Fixed-Cost Project', short: 'Project quote', icon: ClipboardList, iconCls: 'bg-violet-500', d: 'Request fixed quotes from matched pros · Unlimited quotes' },
];
export const jobSizeLabel = (v) => (JOB_SIZES.find((x) => x.v === v) || {}).short || 'Project quote';

const StepTitle = ({ n, children }) => (
  <div className="flex items-center gap-2.5 mb-3">
    <span className="w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-semibold flex items-center justify-center">{n}</span>
    <span className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">{children}</span>
  </div>
);

const ChoiceCard = ({ active, onClick, icon: Icon, title, desc, testid }) => (
  <button
    type="button"
    data-testid={testid}
    onClick={onClick}
    aria-pressed={active}
    className={`relative p-4 rounded-2xl border-2 text-left transition-all ${active ? 'border-primary bg-primary/5 shadow-sm' : 'border-border bg-card hover:border-primary/40'}`}
  >
    {active && <Check className="absolute top-3 right-3 w-4 h-4 text-primary" />}
    <Icon className={`w-5 h-5 mb-2 ${active ? 'text-primary' : 'text-muted-foreground'}`} />
    <div className="text-sm font-semibold text-foreground">{title}</div>
    <div className="text-xs text-muted-foreground mt-0.5">{desc}</div>
  </button>
);

/**
 * Job request form.
 *  - page mode (default): the classic Post-a-Job form.
 *  - flow mode: guided steps used in the Book panel — property type → describe/browse → quotation type → details.
 * Props: preset, flow, onCancel, onNavigate (called before leaving the page)
 */
export default function JobRequestForm({ preset = {}, flow = false, onCancel, onNavigate }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [saving, setSaving] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [activeTenancies, setActiveTenancies] = useState([]);
  const [routeViaManager, setRouteViaManager] = useState(true);
  const [findMode, setFindMode] = useState(''); // flow only: 'describe' | 'browse'
  const [detailsOpen, setDetailsOpen] = useState(false); // flow only: job details window
  const [properties, setProperties] = useState([]);
  const canSaveProperties = PROPERTY_ROLES.has(user?.role);
  const [loc, setLoc] = useState({ property_id: null, address: '', lat: null, lng: null, save: canSaveProperties, save_name: '' });

  useEffect(() => {
    if (!canSaveProperties) return;
    api.get('/properties/mine')
      .then((r) => {
        const list = r.data || [];
        setProperties(list);
        const main = list.find((p) => p.is_primary) || list[0];
        setLoc((l) => (l.property_id || l.address ? l : main
          ? { property_id: main.property_id, address: main.address, lat: main.lat, lng: main.lng, save: false, save_name: '' }
          : { ...l, save: true }));
      })
      .catch(() => setProperties([]));
  }, [canSaveProperties]);

  useEffect(() => {
    // Only tenants (customer role) should see the "route via manager" option
    if (user?.role !== 'customer') return;
    api.get('/tenancies/mine')
      .then((r) => setActiveTenancies((r.data || []).filter((t) => t.status === 'active')))
      .catch(() => setActiveTenancies([]));
  }, [user?.role]);

  const initialServiceType = flow ? '' : (preset.propertyType
    || preset.service_type
    || (user?.role && COMMERCIAL_DEFAULT_ROLES.has(user.role) ? 'commercial' : 'residential'));

  const [form, setForm] = useState({
    title: preset.title || '',
    description: preset.description || '',
    service_type: initialServiceType,
    category: preset.category || '',
    category_name: preset.category_name || '',
    category_icon: preset.category_icon || '',
    category_color: preset.category_color || '',
    subcategory: preset.subcategory || '',
    subcategory_name: preset.subcategory_name || '',
    budget_min: '',
    budget_max: '',
    urgency: 'flexible',
    mode: OPEN_MODE,
    pricing_type: flow ? '' : (preset.pricing_type || 'large_quote'),
    budget_or_estimate: '',
    preferred_date: '',
    photos: preset.photos || [],
  });

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  // Auto-detect the service from title + description until the user picks one manually
  const [manualPick, setManualPick] = useState(false);
  const [autoPicked, setAutoPicked] = useState(false);
  const detected = useServiceDetect(form.service_type ? `${form.title} ${form.description}` : '', form.service_type);
  useEffect(() => {
    if (manualPick || !detected.match) return;
    if (form.category && !autoPicked) return; // keep a preset the user arrived with
    applyService(detected.match);
    setAutoPicked(true);
  }, [detected]);

  const applyService = (sel) => setForm((f) => ({ ...f, ...serviceFields(sel) }));

  const changeServiceType = (t) => {
    if (t === form.service_type) return;
    // A service picked from the search bar resolves to the matching entry in the chosen taxonomy
    const variant = preset.suggestion?.[t];
    setManualPick(!!variant);
    setAutoPicked(false);
    setForm((f) => ({ ...f, service_type: t, ...(variant ? serviceFields(variant) : EMPTY_SERVICE) }));
  };

  const pickProperty = (p) => {
    setLoc({ property_id: p.property_id, address: p.address, lat: p.lat, lng: p.lng, save: false, save_name: '' });
    if (p.property_type && form.service_type && p.property_type !== form.service_type) {
      changeServiceType(p.property_type);
      toast.info(`Property type switched to ${p.property_type === 'commercial' ? 'Commercial' : 'Residential'} for ${p.name || 'this property'}`);
    }
  };

  const handleServicePicked = (sel) => {
    setManualPick(true);
    setAutoPicked(false);
    applyService(sel);
  };

  const browseProviders = () => {
    onNavigate?.();
    if (form.category) {
      navigate(providersLink({
        category_id: form.category, subcategory_id: form.subcategory,
        category_name: form.category_name, subcategory_name: form.subcategory_name,
      }));
    } else {
      navigate(`/find-providers?${new URLSearchParams({ q: form.title }).toString()}`);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!form.title || !form.category) {
      toast.error('Please pick a service and enter a title');
      return;
    }
    if (!form.pricing_type) {
      toast.error('Please choose a job size');
      return;
    }
    if (form.pricing_type !== 'large_quote' && !(Number(form.budget_or_estimate) > 0)) {
      toast.error(form.pricing_type === 'hourly' ? 'Please enter the estimated hours' : 'Please enter your target price');
      return;
    }
    if (!loc.address.trim()) {
      toast.error('Please choose a property or search an address');
      return;
    }
    setSaving(true);
    try {
      let propertyId = loc.property_id;
      if (!propertyId && loc.save && canSaveProperties) {
        try {
          const pr = await api.post('/properties', {
            address: loc.address.trim(), name: (loc.save_name || '').trim() || null,
            property_type: form.service_type || 'residential', lat: loc.lat, lng: loc.lng,
          });
          propertyId = pr.data.property_id;
        } catch {
          toast.error('Could not save the property — posting the job anyway');
        }
      }
      const shouldRoute = activeTenancies.length > 0 && routeViaManager;
      const payload = {
        title: form.title,
        description: form.description,
        category: form.category,
        subcategory: form.subcategory || null,
        service_type: form.service_type,
        location: loc.address.trim(),
        property_id: propertyId || null,
        location_lat: loc.lat ?? null,
        location_lng: loc.lng ?? null,
        budget_min: form.pricing_type === 'large_quote' && form.budget_min ? Number(form.budget_min) : null,
        budget_max: form.pricing_type === 'large_quote' && form.budget_max ? Number(form.budget_max) : null,
        pricing_type: form.pricing_type,
        budget_or_estimate: form.pricing_type !== 'large_quote' && form.budget_or_estimate ? Number(form.budget_or_estimate) : null,
        preferred_date: form.preferred_date || null,
        urgency: form.urgency,
        mode: form.mode,
        photos: form.photos,
        route_via_manager: shouldRoute,
        tenancy_id: shouldRoute ? activeTenancies[0].tenancy_id : null,
      };
      const res = await api.post('/jobs', payload);
      const n = res.data.matched_count || 0;
      toast.success(shouldRoute
        ? 'Request sent to your manager for approval'
        : n ? `Job posted — ${n} specialised pro${n === 1 ? '' : 's'} notified` : 'Job posted — open to all pros on the job board');
      onNavigate?.();
      navigate(`/jobs/${res.data.job_id}`);
    } catch {
      toast.error('Failed to post job');
    } finally {
      setSaving(false);
    }
  };

  const CategoryIcon = form.category_icon && LucideIcons[form.category_icon] ? LucideIcons[form.category_icon] : Layers;
  const serviceTypeLabel = form.service_type === 'commercial' ? 'Commercial' : 'Residential';

  const serviceCard = (
    <div>
      <Label>Service</Label>
      <button
        type="button"
        data-testid="post-job-open-picker"
        onClick={() => setPickerOpen(true)}
        className={`mt-1.5 w-full flex items-center gap-3 p-3.5 rounded-xl border transition-colors text-left ${form.category ? 'border-primary/40 bg-primary/5' : 'border-border hover:border-primary/40'}`}
      >
        {form.category ? (
          <>
            <div className="rounded-lg flex items-center justify-center text-white shrink-0" style={{ backgroundColor: form.category_color || '#3B82F6', width: 36, height: 36 }}>
              <CategoryIcon className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs text-muted-foreground">{autoPicked && <span className="text-primary font-medium" data-testid="post-job-auto-detected">Auto-detected · </span>}{form.category_name}</div>
              <div className="text-sm font-semibold text-foreground truncate" data-testid="post-job-service-name">{form.subcategory_name || 'Any service in this category'}</div>
            </div>
            <Badge variant="outline" className="ml-auto text-xs">Change</Badge>
          </>
        ) : (
          <>
            <div className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center text-muted-foreground shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-semibold text-foreground">Choose a service</div>
              <div className="text-xs text-muted-foreground">Browse {serviceTypeLabel} categories &amp; subcategories</div>
            </div>
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          </>
        )}
      </button>
      {autoPicked && <DetectedAlternatives alternatives={detected.alternatives} onPick={(a) => { applyService(a); setManualPick(true); setAutoPicked(false); }} />}
    </div>
  );

  const tenancyBlock = (
    <>
      {user?.role === 'customer' && activeTenancies.length > 0 && (
        <div className="p-4 rounded-xl border border-primary/30 bg-primary/5" data-testid="tenancy-routing-banner">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary/15 text-primary flex items-center justify-center shrink-0">
              <KeyRound className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-foreground">
                Send this to your manager for approval?
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">
                Linked with <span className="text-foreground font-medium">{activeTenancies[0].approver?.name || activeTenancies[0].approver_email}</span>{activeTenancies[0].label ? ` · ${activeTenancies[0].label}` : ''}. Quotes &amp; invoices will bill to them.
              </div>
              <div className="mt-3 flex items-center gap-2">
                <button
                  type="button"
                  data-testid="route-via-manager-on"
                  onClick={() => setRouteViaManager(true)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${routeViaManager ? 'bg-primary text-primary-foreground border-primary' : 'text-muted-foreground border-border hover:border-primary/50'}`}
                >
                  <ShieldCheck className="w-3 h-3" /> Send to manager
                </button>
                <button
                  type="button"
                  data-testid="route-via-manager-off"
                  onClick={() => setRouteViaManager(false)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${!routeViaManager ? 'bg-foreground text-background border-foreground' : 'text-muted-foreground border-border hover:border-primary/50'}`}
                >
                  Book on my own
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {user?.role === 'customer' && activeTenancies.length === 0 && (
        <div className="p-3 rounded-xl border border-dashed border-border text-xs text-muted-foreground flex items-center gap-2" data-testid="link-manager-hint">
          <KeyRound className="w-3.5 h-3.5 shrink-0" />
          <span className="flex-1">Renting? <Link to="/tenancies" onClick={() => onNavigate?.()} className="text-primary font-medium hover:underline">Link your landlord/manager</Link> to route maintenance requests for approval.</span>
        </div>
      )}
    </>
  );

  const detailFields = (
    <>
      <div>
        <Label>Job title</Label>
        <Input data-testid="post-job-title" value={form.title} onChange={(e) => update('title', e.target.value)} placeholder="e.g. Fix leaking kitchen tap" required className="mt-1.5" />
      </div>

      <div>
        <Label>Description</Label>
        <Textarea data-testid="post-job-description" value={form.description} onChange={(e) => update('description', e.target.value)} rows={4} placeholder="Describe the problem or work needed" required className="mt-1.5" />
      </div>

      <div>
        <Label>Photos & videos <span className="text-muted-foreground font-normal">(optional)</span></Label>
        <div className="mt-1.5">
          <MediaUploader value={form.photos} onChange={(v) => update('photos', v)} testid="post-job-media" />
        </div>
      </div>

      <div>
        <Label>Location</Label>
        <div className="mt-1.5">
          <JobLocationPicker properties={properties} value={loc} onChange={setLoc} onPickProperty={pickProperty} canSave={canSaveProperties} />
        </div>
      </div>

      <div>
        <Label>Urgency</Label>
        <RadioGroup value={form.urgency} onValueChange={(v) => update('urgency', v)} className="mt-2 grid grid-cols-2 gap-2">
          {[
            { v: 'asap', l: 'ASAP - Urgent' },
            { v: 'this_week', l: 'Within 1 week' },
            { v: 'within_month', l: 'Within a month' },
            { v: 'flexible', l: 'Flexible' },
          ].map((o) => (
            <label key={o.v} className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-colors ${form.urgency === o.v ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}>
              <RadioGroupItem value={o.v} id={o.v} />
              <span className="text-sm text-foreground">{o.l}</span>
            </label>
          ))}
        </RadioGroup>
      </div>

      {form.pricing_type === 'small_fixed' && (
        <div>
          <Label>Target fixed price ($)</Label>
          <Input data-testid="post-job-target-price" type="number" min="1" value={form.budget_or_estimate} onChange={(e) => update('budget_or_estimate', e.target.value)} placeholder="e.g. 150" className="mt-1.5" />
        </div>
      )}
      {form.pricing_type === 'hourly' && (
        <div>
          <Label>Estimated hours</Label>
          <Input data-testid="post-job-est-hours" type="number" min="0.5" step="0.5" value={form.budget_or_estimate} onChange={(e) => update('budget_or_estimate', e.target.value)} placeholder="e.g. 4" className="mt-1.5" />
        </div>
      )}
      {form.pricing_type === 'large_quote' && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Budget min ($) <span className="text-muted-foreground font-normal">(optional)</span></Label>
            <Input type="number" value={form.budget_min} onChange={(e) => update('budget_min', e.target.value)} placeholder="0" className="mt-1.5" />
          </div>
          <div>
            <Label>Budget max ($) <span className="text-muted-foreground font-normal">(optional)</span></Label>
            <Input type="number" value={form.budget_max} onChange={(e) => update('budget_max', e.target.value)} placeholder="0" className="mt-1.5" />
          </div>
        </div>
      )}

      <div>
        <Label>Preferred date <span className="text-muted-foreground font-normal">(optional)</span></Label>
        <div className="relative mt-1.5">
          <CalendarDays className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          <Input data-testid="post-job-preferred-date" type="date" min={new Date().toISOString().slice(0, 10)} value={form.preferred_date} onChange={(e) => update('preferred_date', e.target.value)} className="pl-9" />
        </div>
      </div>
    </>
  );

  const jobSizeCards = (onPick, testPrefix) => (
    <div className="space-y-2.5">
      {JOB_SIZES.map((q) => {
        const active = form.pricing_type === q.v;
        const Icon = q.icon;
        return (
          <button
            key={q.v}
            type="button"
            data-testid={`${testPrefix}-${q.v}`}
            aria-pressed={active}
            onClick={() => onPick(q.v)}
            className={`w-full group flex items-center gap-4 p-4 rounded-2xl border-2 text-left transition-all ${active ? 'border-primary bg-primary/5 shadow-sm' : 'border-border bg-card hover:border-primary/40'}`}
          >
            <div className={`w-11 h-11 rounded-xl ${q.iconCls} flex items-center justify-center text-white shrink-0`}>
              <Icon className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-foreground">{q.l}</div>
              <div className="text-xs sm:text-sm text-muted-foreground mt-0.5">{q.d}</div>
            </div>
            <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-all shrink-0" />
          </button>
        );
      })}
    </div>
  );

  const picker = (
    <ServicePicker
      open={pickerOpen}
      onOpenChange={setPickerOpen}
      serviceType={form.service_type || 'residential'}
      value={form.category ? { category_id: form.category, subcategory_id: form.subcategory } : undefined}
      onSelect={handleServicePicked}
    />
  );

  /* ---------------- FLOW MODE (Book panel) ---------------- */
  if (flow) {
    return (
      <div className="space-y-8" data-testid="booking-flow">
        <section>
          <StepTitle n={1}>Property type</StepTitle>
          <div className="grid grid-cols-2 gap-3">
            <ChoiceCard testid="booking-type-residential" active={form.service_type === 'residential'} onClick={() => changeServiceType('residential')} icon={HomeIcon} title="Residential" desc="Homes, tenants, holiday rentals" />
            <ChoiceCard testid="booking-type-commercial" active={form.service_type === 'commercial'} onClick={() => changeServiceType('commercial')} icon={Building2} title="Commercial" desc="Offices, retail, industrial, facilities" />
          </div>
        </section>

        {form.service_type && (
          <section className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <StepTitle n={2}>How do you want to find a pro?</StepTitle>
            <div className="grid grid-cols-2 gap-3">
              <ChoiceCard testid="booking-find-describe" active={findMode === 'describe'} onClick={() => setFindMode('describe')} icon={Pencil} title="Describe your job" desc="Tell pros what's needed and get offers" />
              <ChoiceCard testid="booking-find-browse" active={findMode === 'browse'} onClick={() => setFindMode('browse')} icon={Users} title="Browse providers" desc="Pick a pro yourself from the directory" />
            </div>
          </section>
        )}

        {form.service_type && findMode === 'browse' && (
          <section className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300" data-testid="booking-browse-section">
            {serviceCard}
            <Button type="button" onClick={browseProviders} data-testid="booking-browse-go" className="w-full h-12 text-base">
              <Users className="w-4 h-4 mr-2" /> See {form.subcategory_name || form.category_name || 'matching'} providers
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </section>
        )}

        {form.service_type && findMode === 'describe' && (
          <section className="animate-in fade-in slide-in-from-bottom-2 duration-300" data-testid="booking-quote-section">
            <StepTitle n={3}>Job size</StepTitle>
            {jobSizeCards((v) => { update('pricing_type', v); setDetailsOpen(true); }, 'booking-size')}
          </section>
        )}

        {/* Second full-screen window: job details */}
        <Sheet open={detailsOpen} onOpenChange={setDetailsOpen}>
          <SheetContent
            side="right"
            hideClose
            className="w-full sm:max-w-none max-w-none p-0 border-0 flex flex-col gap-0"
            data-testid="booking-details-panel"
            onOpenAutoFocus={(e) => e.preventDefault()}
          >
            <div className="shrink-0 flex items-center gap-3 px-4 sm:px-6 h-16 border-b border-border bg-background/95 backdrop-blur">
              <button type="button" onClick={() => setDetailsOpen(false)} data-testid="booking-details-back" className="p-2 -ml-2 rounded-full hover:bg-accent text-foreground" aria-label="Back to options">
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div className="min-w-0">
                <SheetTitle className="text-base font-semibold text-foreground leading-tight">Post a Job</SheetTitle>
                <SheetDescription className="text-xs text-muted-foreground truncate">
                  {serviceTypeLabel} · <span data-testid="booking-details-size">{jobSizeLabel(form.pricing_type)}</span>
                </SheetDescription>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto overscroll-contain">
              <form onSubmit={submit} className="max-w-2xl mx-auto px-4 sm:px-6 py-6 pb-16 space-y-5" data-testid="booking-details-section">
                {tenancyBlock}
                {serviceCard}
                {detailFields}
                <div className="flex gap-3 pt-2">
                  <Button type="button" variant="outline" onClick={() => setDetailsOpen(false)} className="flex-1">Back</Button>
                  <Button data-testid="post-job-submit" type="submit" disabled={saving} className="flex-1">
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Post Job'}
                  </Button>
                </div>
              </form>
            </div>
          </SheetContent>
        </Sheet>
        {picker}
      </div>
    );
  }

  /* ---------------- PAGE MODE (classic Post-a-Job) ---------------- */
  return (
    <>
      <form onSubmit={submit} className="mt-6 space-y-5 bg-card border border-border rounded-2xl p-6">
        {tenancyBlock}
        {/* Service type toggle */}
        <div>
          <Label>Property type</Label>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <button
              type="button"
              data-testid="post-job-service-type-residential"
              onClick={() => changeServiceType('residential')}
              className={`p-3 rounded-xl border-2 text-left transition-all ${form.service_type === 'residential' ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}
            >
              <div className="flex items-center gap-2">
                <HomeIcon className={`w-4 h-4 ${form.service_type === 'residential' ? 'text-primary' : 'text-muted-foreground'}`} />
                <span className="text-sm font-semibold text-foreground">Residential</span>
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">Homes, tenants, holiday rentals</div>
            </button>
            <button
              type="button"
              data-testid="post-job-service-type-commercial"
              onClick={() => changeServiceType('commercial')}
              className={`p-3 rounded-xl border-2 text-left transition-all ${form.service_type === 'commercial' ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}
            >
              <div className="flex items-center gap-2">
                <Building2 className={`w-4 h-4 ${form.service_type === 'commercial' ? 'text-primary' : 'text-muted-foreground'}`} />
                <span className="text-sm font-semibold text-foreground">Commercial</span>
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">Offices, retail, industrial, facilities</div>
            </button>
          </div>
        </div>

        <div>
          <Label>Job size</Label>
          <div className="mt-2">{jobSizeCards((v) => update('pricing_type', v), 'post-job-size')}</div>
        </div>
        {serviceCard}
        {detailFields}

        <div className="flex gap-3 pt-2">
          <Button type="button" variant="outline" onClick={() => (onCancel ? onCancel() : navigate(-1))} className="flex-1">Cancel</Button>
          <Button data-testid="post-job-submit" type="submit" disabled={saving} className="flex-1">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Post Job'}
          </Button>
        </div>
      </form>
      {picker}
    </>
  );
}
