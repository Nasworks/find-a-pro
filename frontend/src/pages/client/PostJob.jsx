import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import * as LucideIcons from 'lucide-react';
import { ArrowLeft, MapPin, Loader2, Home as HomeIcon, Building2, ChevronRight, Sparkles, Layers, KeyRound, ShieldCheck } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { RadioGroup, RadioGroupItem } from '../../components/ui/radio-group';
import { Badge } from '../../components/ui/badge';
import ServicePicker from '../../components/ServicePicker';
import { useServiceDetect, DetectedAlternatives } from '../../components/ServiceDetect';
import { MediaUploader } from '../../components/MediaUploader';
import { useAuth } from '../../context/AuthContext';
import api from '../../lib/api';
import { toast } from 'sonner';

// Roles that default to commercial when they hit Post-a-Job
const COMMERCIAL_DEFAULT_ROLES = new Set(['facilities', 'property']);

export default function PostJob() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const preset = location.state || {};
  const [saving, setSaving] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [activeTenancies, setActiveTenancies] = useState([]);
  const [routeViaManager, setRouteViaManager] = useState(true);

  useEffect(() => {
    // Only tenants (customer role) should see the "route via manager" option
    if (user?.role !== 'customer') return;
    api.get('/tenancies/mine')
      .then((r) => setActiveTenancies((r.data || []).filter((t) => t.status === 'active')))
      .catch(() => setActiveTenancies([]));
  }, [user?.role]);

  const initialServiceType = preset.propertyType
    || preset.service_type
    || (user?.role && COMMERCIAL_DEFAULT_ROLES.has(user.role) ? 'commercial' : 'residential');

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
    location: 'Auckland',
    budget_min: '',
    budget_max: '',
    urgency: 'flexible',
    mode: preset.mode || 'quotes',
    photos: preset.photos || [],
  });

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  // Auto-detect the service from title + description until the user picks one manually
  const [manualPick, setManualPick] = useState(false);
  const [autoPicked, setAutoPicked] = useState(false);
  const detected = useServiceDetect(`${form.title} ${form.description}`, form.service_type);
  useEffect(() => {
    if (manualPick || !detected.match) return;
    if (form.category && !autoPicked) return; // keep a preset the user arrived with
    applyService(detected.match);
    setAutoPicked(true);
  }, [detected]); // eslint-disable-line react-hooks/exhaustive-deps

  const applyService = (sel) => setForm((f) => ({
    ...f,
    category: sel.category_id,
    category_name: sel.category_name,
    category_icon: sel.category_icon,
    category_color: sel.category_color,
    subcategory: sel.subcategory_id,
    subcategory_name: sel.subcategory_name,
  }));

  const changeServiceType = (t) => {
    // Reset category when switching types (taxonomies differ)
    setForm((f) => ({
      ...f,
      service_type: t,
      category: '',
      category_name: '',
      category_icon: '',
      category_color: '',
      subcategory: '',
      subcategory_name: '',
    }));
  };

  const handleServicePicked = (sel) => {
    setManualPick(true);
    setAutoPicked(false);
    setForm((f) => ({
      ...f,
      category: sel.category_id,
      category_name: sel.category_name,
      category_icon: sel.category_icon,
      category_color: sel.category_color,
      subcategory: sel.subcategory_id,
      subcategory_name: sel.subcategory_name,
    }));
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!form.title || !form.category) {
      toast.error('Please pick a service and enter a title');
      return;
    }
    setSaving(true);
    try {
      const shouldRoute = activeTenancies.length > 0 && routeViaManager;
      const payload = {
        title: form.title,
        description: form.description,
        category: form.category,
        subcategory: form.subcategory || null,
        service_type: form.service_type,
        location: form.location,
        budget_min: form.budget_min ? Number(form.budget_min) : null,
        budget_max: form.budget_max ? Number(form.budget_max) : null,
        urgency: form.urgency,
        mode: form.mode,
        photos: form.photos,
        route_via_manager: shouldRoute,
        tenancy_id: shouldRoute ? activeTenancies[0].tenancy_id : null,
      };
      const res = await api.post('/jobs', payload);
      toast.success(shouldRoute
        ? 'Request sent to your manager for approval'
        : 'Job posted — pros will be notified');
      navigate(`/jobs/${res.data.job_id}`);
    } catch {
      toast.error('Failed to post job');
    } finally {
      setSaving(false);
    }
  };

  const CategoryIcon = form.category_icon && LucideIcons[form.category_icon] ? LucideIcons[form.category_icon] : Layers;
  const serviceTypeLabel = form.service_type === 'commercial' ? 'Commercial' : 'Residential';

  return (
    <div className="max-w-2xl mx-auto p-6">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-4 h-4" /> Back
      </button>
      <h1 className="text-3xl font-bold text-foreground">Post a Job</h1>
      <p className="text-muted-foreground mt-1">Tell us the details — we&apos;ll match you with the right pros.</p>

      <form onSubmit={submit} className="mt-6 space-y-5 bg-card border border-border rounded-2xl p-6">
        {/* Tenancy routing banner */}
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
            <span className="flex-1">Renting? <Link to="/tenancies" className="text-primary font-medium hover:underline">Link your landlord/manager</Link> to route maintenance requests for approval.</span>
          </div>
        )}
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

        {/* SERVICE PICKER TRIGGER */}
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
                  <div className="text-sm font-semibold text-foreground truncate">{form.subcategory_name || 'Any service in this category'}</div>
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
          <div className="relative mt-1.5">
            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input data-testid="post-job-location" value={form.location} onChange={(e) => update('location', e.target.value)} className="pl-9" />
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

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Budget min ($)</Label>
            <Input type="number" value={form.budget_min} onChange={(e) => update('budget_min', e.target.value)} placeholder="0" className="mt-1.5" />
          </div>
          <div>
            <Label>Budget max ($)</Label>
            <Input type="number" value={form.budget_max} onChange={(e) => update('budget_max', e.target.value)} placeholder="0" className="mt-1.5" />
          </div>
        </div>

        <div>
          <Label>How would you like to receive offers?</Label>
          <RadioGroup value={form.mode} onValueChange={(v) => update('mode', v)} className="mt-2 space-y-2">
            {[
              { v: 'instant', l: 'Instant Booking', d: 'First nearby pro accepts' },
              { v: 'quotes', l: 'Get 3 Quotes', d: 'Compare & chat with 3 pros' },
              { v: 'bids', l: 'Open Bidding', d: 'Public job — receive multiple bids' },
            ].map((o) => (
              <label key={o.v} className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${form.mode === o.v ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}>
                <RadioGroupItem value={o.v} id={`mode-${o.v}`} className="mt-0.5" />
                <div>
                  <div className="text-sm font-medium text-foreground">{o.l}</div>
                  <div className="text-xs text-muted-foreground">{o.d}</div>
                </div>
              </label>
            ))}
          </RadioGroup>
        </div>

        <div className="flex gap-3 pt-2">
          <Button type="button" variant="outline" onClick={() => navigate(-1)} className="flex-1">Cancel</Button>
          <Button data-testid="post-job-submit" type="submit" disabled={saving} className="flex-1">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Post Job'}
          </Button>
        </div>
      </form>

      <ServicePicker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        serviceType={form.service_type}
        value={form.category ? { category_id: form.category, subcategory_id: form.subcategory } : undefined}
        onSelect={handleServicePicked}
      />
    </div>
  );
}
