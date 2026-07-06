import React, { useEffect, useState } from 'react';
import { Calculator, TrendingUp, Info } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';

export default function CostEstimator() {
  const [guide, setGuide] = useState([]);
  const [category, setCategory] = useState('');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    api.get('/cost-guide')
      .then((r) => setGuide(r.data))
      .catch((err) => console.error('[CostEstimator] load failed:', err));
  }, []);

  const categories = [...new Set(guide.map((g) => g.category))];
  const filtered = category ? guide.filter((g) => g.category === category) : guide;

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2"><Calculator className="w-5 h-5 text-primary" /> Cost Estimator</h1>
        <p className="text-sm text-muted-foreground">Market rates from 12,000+ recent NZ jobs</p>
      </div>

      <div className="bg-gradient-to-r from-primary/5 to-blue-500/5 border border-primary/20 rounded-2xl p-4 mb-6 flex items-start gap-3">
        <Info className="w-5 h-5 text-primary shrink-0 mt-0.5" />
        <div className="text-sm">
          <div className="font-semibold text-foreground">How does it work?</div>
          <p className="text-muted-foreground mt-1">These are median prices from real Dispatchr jobs. Actual quotes vary based on site conditions, materials & urgency.</p>
        </div>
      </div>

      <div className="mb-6">
        <Label>Filter by category</Label>
        <Select value={category || 'all'} onValueChange={(v) => setCategory(v === 'all' ? '' : v)}>
          <SelectTrigger className="mt-1.5"><SelectValue placeholder="All categories" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {filtered.map((g) => (
          <button key={`${g.category}-${g.job}`} onClick={() => setSelected(g)} className={`text-left bg-card border rounded-2xl p-4 hover:border-primary/40 transition-colors ${selected?.job === g.job ? 'border-primary shadow-sm' : 'border-border'}`}>
            <div className="flex items-start justify-between">
              <div>
                <div className="font-medium text-foreground">{g.job}</div>
                <div className="text-xs text-muted-foreground">{g.category} · per {g.unit}</div>
              </div>
              <Badge variant="secondary">${g.avg}</Badge>
            </div>
            <div className="mt-3 text-xs text-muted-foreground flex items-center gap-3">
              <span>Low <span className="text-foreground font-semibold">${g.low}</span></span>
              <span>Avg <span className="text-primary font-semibold">${g.avg}</span></span>
              <span>High <span className="text-foreground font-semibold">${g.high}</span></span>
            </div>
            <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden"><div className="h-full bg-gradient-to-r from-emerald-500 via-primary to-rose-500" /></div>
          </button>
        ))}
      </div>
    </div>
  );
}
