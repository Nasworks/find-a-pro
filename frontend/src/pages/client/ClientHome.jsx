import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, MessageSquare, ClipboardList, Camera, Mic, Home as HomeIcon, Building, Sparkles, ArrowRight, Layers, Wrench, Search } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Textarea } from '../../components/ui/textarea';
import { Badge } from '../../components/ui/badge';
import ServicePicker from '../../components/ServicePicker';
import api from '../../lib/api';

const RESIDENTIAL_QUICK = [
  { label: 'Leaking tap', cat: 'plumbing-gas', sub: 'leak-repairs' },
  { label: 'Blocked drain', cat: 'plumbing-gas', sub: 'blocked-drains' },
  { label: 'Heat pump install', cat: 'heating-cooling-ventilation', sub: 'heat-pump-installation' },
  { label: 'Interior painting', cat: 'painting-interior-finishes', sub: 'interior-painting' },
  { label: 'Roof repair', cat: 'roofing-guttering', sub: 'roof-repairs' },
  { label: 'Handyman', cat: 'general-home-maintenance', sub: 'handyman-services' },
];

const COMMERCIAL_QUICK = [
  { label: 'LED retrofit', cat: 'electrical', sub: 'led-retrofits' },
  { label: 'HVAC service', cat: 'hvac-mechanical', sub: 'commercial-air-conditioning' },
  { label: 'Roof leak', cat: 'roofing-waterproofing', sub: 'leak-repairs' },
  { label: 'CCTV install', cat: 'security-systems', sub: 'cctv-installation' },
  { label: 'Office fit-out', cat: 'renovations-fitouts', sub: 'office-renovations' },
  { label: 'Handyman', cat: 'building-maintenance', sub: 'commercial-handyman' },
];

export default function ClientHome() {
  const [propertyType, setPropertyType] = useState('residential');
  const [description, setDescription] = useState('');
  const [pickerOpen, setPickerOpen] = useState(false);
  const [picked, setPicked] = useState(null);
  const navigate = useNavigate();

  const proceed = (mode) => {
    navigate('/post-job', {
      state: {
        description,
        propertyType,
        mode,
        ...(picked ? {
          category: picked.category_id,
          category_name: picked.category_name,
          category_icon: picked.category_icon,
          category_color: picked.category_color,
          subcategory: picked.subcategory_id,
          subcategory_name: picked.subcategory_name,
        } : {}),
      },
    });
  };

  const quickPick = (q) => {
    navigate('/post-job', {
      state: {
        propertyType,
        category: q.cat,
        subcategory: q.sub,
        subcategory_name: q.label,
      },
    });
  };

  const changePropertyType = (t) => {
    setPropertyType(t);
    setPicked(null); // taxonomies differ
  };

  const quickTags = propertyType === 'commercial' ? COMMERCIAL_QUICK : RESIDENTIAL_QUICK;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-8 p-6 lg:p-10 max-w-7xl mx-auto">
      <div className="space-y-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight">
            Your home, managed <span className="bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">intelligently.</span>
          </h1>
          <p className="mt-4 text-muted-foreground max-w-2xl">
            Describe what you need — we&apos;ll instantly match you with a verified, top-rated local professional.
          </p>
        </div>

        <div className="bg-card border border-border rounded-2xl p-6 shadow-sm">
          <div className="flex gap-2 mb-4">
            <button data-testid="clienthome-type-residential" onClick={() => changePropertyType('residential')} className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${propertyType === 'residential' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>
              <HomeIcon className="w-3.5 h-3.5 inline mr-1.5" /> Residential
            </button>
            <button data-testid="clienthome-type-commercial" onClick={() => changePropertyType('commercial')} className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${propertyType === 'commercial' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>
              <Building className="w-3.5 h-3.5 inline mr-1.5" /> Commercial
            </button>
          </div>
          <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Be as specific as you like... e.g. 'Leaking kitchen tap, dripping steadily'" rows={4} className="border-0 bg-muted/40 focus:bg-background resize-none text-base" />
          <div className="flex items-center justify-between mt-3">
            <div className="flex gap-2">
              <button className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors" title="Voice input"><Mic className="w-4 h-4" /></button>
              <button className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors" title="Add photo"><Camera className="w-4 h-4" /></button>
            </div>
            <Button onClick={() => proceed('quotes')} disabled={!description.trim()} className="h-10">
              <Search className="w-4 h-4 mr-2" /> Find a Pro
            </Button>
          </div>

          <div className="mt-5 pt-5 border-t border-border">
            {picked && (
              <div className="mb-4 flex items-center gap-3 p-3 rounded-xl border border-primary/40 bg-primary/5">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center text-white shrink-0" style={{ backgroundColor: picked.category_color }}>
                  <Wrench className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-muted-foreground">{picked.category_name}</div>
                  <div className="text-sm font-semibold text-foreground truncate">{picked.subcategory_name}</div>
                </div>
                <button onClick={() => setPicked(null)} className="text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded hover:bg-accent">Clear</button>
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              {quickTags.map((t) => (
                <button key={t.label} data-testid={`clienthome-quick-${t.sub}`} onClick={() => quickPick(t)} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-muted hover:bg-accent text-sm text-foreground transition-colors">
                  <span>{t.label}</span>
                </button>
              ))}
            </div>
            <button data-testid="clienthome-browse-services" onClick={() => setPickerOpen(true)} className="mt-4 inline-flex items-center gap-2 text-sm text-primary font-medium hover:underline">
              <Layers className="w-4 h-4" /> Browse all {propertyType === 'commercial' ? '100+ commercial' : '120+ residential'} services
            </button>
          </div>
        </div>

        <div className="space-y-3">
          <div className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">How would you like to proceed?</div>
          <button onClick={() => proceed('instant')} className="w-full group flex items-center gap-4 p-5 rounded-2xl bg-gradient-to-r from-primary/10 to-blue-500/10 border border-primary/20 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/10 transition-all text-left">
            <div className="w-12 h-12 rounded-xl bg-primary flex items-center justify-center text-white shrink-0">
              <Zap className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground">Request Booking</span>
                <Badge className="bg-primary text-primary-foreground">INSTANT</Badge>
              </div>
              <div className="text-sm text-muted-foreground mt-0.5">Small jobs · 3 nearest pros notified · First to accept wins · Urgent or scheduled</div>
            </div>
            <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
          </button>

          <button onClick={() => proceed('quotes')} className="w-full group flex items-center gap-4 p-5 rounded-2xl bg-card border border-border hover:border-primary/40 hover:shadow-md transition-all text-left">
            <div className="w-12 h-12 rounded-xl bg-emerald-500 flex items-center justify-center text-white shrink-0">
              <MessageSquare className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground">Get 3 Quotes</span>
                <Badge variant="secondary" className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">FREE</Badge>
              </div>
              <div className="text-sm text-muted-foreground mt-0.5">3 closest providers · Chat & negotiate · No commitment until you accept</div>
            </div>
            <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
          </button>

          <button onClick={() => proceed('bids')} className="w-full group flex items-center gap-4 p-5 rounded-2xl bg-card border border-border hover:border-primary/40 hover:shadow-md transition-all text-left">
            <div className="w-12 h-12 rounded-xl bg-violet-500 flex items-center justify-center text-white shrink-0">
              <ClipboardList className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground">Post a Job for Bids</span>
                <Badge variant="secondary">OPEN</Badge>
              </div>
              <div className="text-sm text-muted-foreground mt-0.5">Post your job publicly · Compare bids · Pick the best value</div>
            </div>
            <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
          </button>
        </div>
      </div>

      <aside className="space-y-4">
        <div className="bg-card border border-border rounded-2xl p-5">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-3">How it works</div>
          {[
            { n: 1, t: 'Describe your job', d: 'Tell us what needs doing — voice, text, or photo.' },
            { n: 2, t: 'Get matched instantly', d: 'We surface verified, top-rated pros near you.' },
            { n: 3, t: 'Book & track in real-time', d: 'Schedule, pay, and follow your pro live.' },
          ].map((s) => (
            <div key={s.n} className="flex gap-3 mb-3 last:mb-0">
              <div className="w-7 h-7 rounded-full bg-primary/10 text-primary text-xs font-semibold flex items-center justify-center shrink-0">{s.n}</div>
              <div>
                <div className="text-sm font-medium text-foreground">{s.t}</div>
                <div className="text-xs text-muted-foreground">{s.d}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-gradient-to-br from-primary to-blue-700 rounded-2xl p-5 text-white">
          <div className="flex items-center gap-2 text-xs font-medium mb-1 opacity-90">
            <Sparkles className="w-3.5 h-3.5" /> Dispatchr Trusted
          </div>
          <div className="font-semibold">Verified Pros. Guaranteed work.</div>
          <div className="text-sm opacity-90 mt-1">Every provider is background-checked, insured and rated by real customers.</div>
          <Button variant="secondary" className="mt-4 h-8 bg-white/20 hover:bg-white/30 text-white border-0">Learn more</Button>
        </div>

        <div className="bg-card border border-border rounded-2xl p-5 text-sm text-muted-foreground space-y-1">
          <div className="font-medium text-foreground mb-2">Dispatchr</div>
          <div>Help · Contact · About</div>
          <div>Terms · Privacy · For Pros</div>
          <div className="mt-3 text-xs">© 2026 Dispatchr. All rights reserved.</div>
        </div>
      </aside>

      <ServicePicker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        serviceType={propertyType}
        value={picked ? { category_id: picked.category_id, subcategory_id: picked.subcategory_id } : undefined}
        onSelect={(sel) => setPicked(sel)}
      />
    </div>
  );
}
