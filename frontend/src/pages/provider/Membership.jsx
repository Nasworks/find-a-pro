import React, { useEffect, useState } from 'react';
import { Check, Sparkles, ShieldCheck, Zap, Users, Crown } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';
import { toast } from 'sonner';

const planIcons = { free: ShieldCheck, starter: Zap, pro: Sparkles, enterprise: Crown };
const planColors = {
  free: 'from-gray-500 to-gray-600',
  starter: 'from-blue-500 to-blue-600',
  pro: 'from-primary to-blue-700',
  enterprise: 'from-amber-500 to-orange-600',
};

export default function Membership() {
  const [plans, setPlans] = useState([]);
  const [current, setCurrent] = useState({ plan: { id: 'free' }, bids_used_this_month: 0 });
  const [billing, setBilling] = useState('month');

  const load = async () => {
    const [p, m] = await Promise.all([api.get('/membership/plans'), api.get('/membership/mine')]);
    setPlans(p.data);
    setCurrent(m.data);
  };
  useEffect(() => { load(); }, []);

  const subscribe = async (plan_id) => {
    await api.post('/membership/subscribe', { plan_id });
    toast.success('Plan updated!');
    load();
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-foreground">Membership Plans</h1>
        <p className="text-sm text-muted-foreground mt-1">Grow your business with priority listings, unlimited bids & premium tools</p>
        <div className="inline-flex mt-4 p-1 rounded-full bg-muted">
          <button onClick={() => setBilling('month')} className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${billing === 'month' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'}`}>Monthly</button>
          <button onClick={() => setBilling('year')} className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${billing === 'year' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'}`}>Yearly <Badge className="ml-1 bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">Save 20%</Badge></button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {plans.map((p) => {
          const Icon = planIcons[p.id] || Sparkles;
          const isCurrent = current.plan?.id === p.id;
          const price = billing === 'year' && p.price > 0 ? Math.round(p.price * 12 * 0.8) : p.price;
          return (
            <div key={p.id} className={`relative bg-card border rounded-2xl p-6 flex flex-col ${p.popular ? 'border-primary shadow-lg shadow-primary/10 scale-105' : 'border-border'}`}>
              {p.popular && <Badge className="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground">MOST POPULAR</Badge>}
              <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${planColors[p.id]} text-white flex items-center justify-center mb-3`}><Icon className="w-5 h-5" /></div>
              <div className="text-lg font-semibold text-foreground">{p.name}</div>
              <div className="mt-2">
                <span className="text-3xl font-bold text-foreground">${price}</span>
                {p.price > 0 && <span className="text-sm text-muted-foreground">/{billing === 'year' ? 'year' : 'mo'}</span>}
                {p.price === 0 && <span className="text-sm text-muted-foreground"> forever</span>}
              </div>
              <ul className="mt-4 space-y-2 flex-1 text-sm">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-foreground/90">
                    <Check className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" /> {f}
                  </li>
                ))}
              </ul>
              <Button onClick={() => subscribe(p.id)} disabled={isCurrent} variant={isCurrent ? 'outline' : (p.popular ? 'default' : 'outline')} className="mt-6 w-full">
                {isCurrent ? 'Current plan' : (p.id === 'free' ? 'Downgrade' : 'Choose plan')}
              </Button>
            </div>
          );
        })}
      </div>

      <div className="mt-10 bg-card border border-border rounded-2xl p-6">
        <div className="font-semibold text-foreground mb-4">Feature comparison</div>
        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted-foreground text-xs uppercase">
                <th className="p-2">Feature</th>
                {plans.map((p) => <th key={p.id} className="p-2 text-center">{p.name}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {[
                ['Monthly bids', ['5', '25', 'Unlimited', 'Unlimited']],
                ['Verified badge', [false, true, true, true]],
                ['Priority in search', [false, true, true, true]],
                ['Featured placement', [false, false, true, true]],
                ['Team management', [false, false, true, true]],
                ['GPS tracking', [false, false, '2 devices', 'Unlimited']],
                ['API access', [false, false, false, true]],
                ['Dedicated support', [false, false, false, true]],
              ].map((row) => (
                <tr key={row[0]}>
                  <td className="p-2 font-medium text-foreground">{row[0]}</td>
                  {row[1].map((v, i) => (
                    <td key={`${row[0]}-col-${i}`} className="p-2 text-center text-muted-foreground">
                      {v === true ? <Check className="w-4 h-4 text-emerald-500 mx-auto" /> : v === false ? '—' : v}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
