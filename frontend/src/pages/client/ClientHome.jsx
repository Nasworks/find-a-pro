import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, MessageSquare, ClipboardList, Camera, Mic, Home as HomeIcon, Building, Sparkles, ArrowRight, ChevronRight, Wrench, Trees, Wind, Hammer, Paintbrush, Refrigerator, Truck, Bug, Search } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Textarea } from '../../components/ui/textarea';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';

const iconMap = { Wrench, Zap, Sparkles, Trees, Wind, Hammer, Paintbrush, Home: HomeIcon, Refrigerator, Truck, Bug };

const quickTags = [
  { label: 'Leaking tap', cat: 'plumbing' },
  { label: 'House clean', cat: 'cleaning' },
  { label: 'Electrician', cat: 'electrical' },
  { label: 'Lawn mowing', cat: 'lawn' },
  { label: 'Heat pump', cat: 'hvac' },
  { label: 'Painting', cat: 'painting' },
];

export default function ClientHome() {
  const [propertyType, setPropertyType] = useState('residential');
  const [description, setDescription] = useState('');
  const [categories, setCategories] = useState([]);
  const [showAllCats, setShowAllCats] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/categories').then((r) => setCategories(r.data)).catch(() => {});
  }, []);

  const proceed = (mode) => {
    navigate('/post-job', { state: { description, propertyType, mode } });
  };

  const quickPick = (cat) => {
    navigate('/post-job', { state: { category: cat, propertyType } });
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-8 p-6 lg:p-10 max-w-7xl mx-auto">
      <div className="space-y-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-bold text-foreground tracking-tight">
            Your home, managed <span className="bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">intelligently.</span>
          </h1>
          <p className="mt-4 text-muted-foreground max-w-2xl">
            Describe what you need — we'll instantly match you with a verified, top-rated local professional.
          </p>
        </div>

        <div className="bg-card border border-border rounded-2xl p-6 shadow-sm">
          <div className="flex gap-2 mb-4">
            <button onClick={() => setPropertyType('residential')} className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${propertyType === 'residential' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>
              <HomeIcon className="w-3.5 h-3.5 inline mr-1.5" /> Residential
            </button>
            <button onClick={() => setPropertyType('commercial')} className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${propertyType === 'commercial' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>
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
            <div className="flex flex-wrap gap-2">
              {quickTags.map((t) => (
                <button key={t.label} onClick={() => quickPick(t.cat)} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-muted hover:bg-accent text-sm text-foreground transition-colors">
                  <span>{t.label}</span>
                </button>
              ))}
            </div>
            <button onClick={() => setShowAllCats(!showAllCats)} className="mt-4 inline-flex items-center gap-2 text-sm text-primary font-medium hover:underline">
              Browse all categories <ChevronRight className={`w-4 h-4 transition-transform ${showAllCats ? 'rotate-90' : ''}`} />
            </button>
            {showAllCats && (
              <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                {categories.map((c) => {
                  const Icon = iconMap[c.icon] || Wrench;
                  return (
                    <button key={c.id} onClick={() => quickPick(c.id)} className="flex items-center gap-2 p-3 rounded-lg border border-border hover:border-primary/50 hover:bg-accent transition-colors text-left">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: c.color + '20', color: c.color }}><Icon className="w-4 h-4" /></div>
                      <span className="text-sm font-medium text-foreground">{c.name}</span>
                    </button>
                  );
                })}
              </div>
            )}
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
    </div>
  );
}
