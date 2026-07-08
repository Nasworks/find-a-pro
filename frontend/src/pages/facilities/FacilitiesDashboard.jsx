import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2, ShieldCheck, Wrench, AlertCircle, Clock, TrendingUp, Users } from 'lucide-react';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import api from '../../lib/api';

const mockSites = [
  { name: 'Auckland CBD Office Tower', address: '123 Queen St, Auckland CBD', sla: '4h response', open_tickets: 3, compliance: 98 },
  { name: 'Westfield Retail Space #204', address: '277 Broadway, Newmarket', sla: '2h response', open_tickets: 1, compliance: 100 },
  { name: 'Industrial Warehouse Zone A', address: '45 Neilson St, Onehunga', sla: '8h response', open_tickets: 5, compliance: 92 },
];

export default function FacilitiesDashboard() {
  const [properties, setProperties] = useState([]);

  useEffect(() => {
    api.get('/properties/mine')
      .then((r) => setProperties(r.data))
      .catch((err) => console.error('[Facilities] failed:', err));
  }, []);

  const openTickets = mockSites.reduce((s, p) => s + p.open_tickets, 0);
  const avgCompliance = Math.round(mockSites.reduce((s, p) => s + p.compliance, 0) / mockSites.length);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <div className="text-xs uppercase text-muted-foreground tracking-wider">Facilities Portal</div>
        <h1 className="text-2xl font-bold text-foreground">Commercial sites & SLA compliance</h1>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon={Building2} label="Sites" value={mockSites.length + properties.length} color="text-violet-500" />
        <StatCard icon={Wrench} label="Open tickets" value={openTickets} color="text-amber-500" />
        <StatCard icon={ShieldCheck} label="SLA compliance" value={`${avgCompliance}%`} color="text-emerald-500" />
        <StatCard icon={Clock} label="Avg response" value="3.2h" color="text-primary" />
      </div>

      <div className="bg-gradient-to-r from-primary to-blue-700 rounded-2xl p-5 text-white">
        <div className="flex items-center gap-2 text-xs font-medium opacity-90"><ShieldCheck className="w-3.5 h-3.5" /> SLA Alert</div>
        <div className="font-semibold mt-1">3 tickets approaching SLA breach</div>
        <div className="text-sm opacity-90">Industrial Warehouse Zone A has 5 open tickets. Preventive maintenance recommended.</div>
        <Button variant="secondary" className="mt-4 bg-white/20 hover:bg-white/30 text-white border-0">View SLA queue</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Link to="/post-job" className="bg-card border border-border rounded-2xl p-5 hover:border-primary/40 transition-colors">
          <div className="w-10 h-10 rounded-lg bg-primary text-white flex items-center justify-center mb-3"><Wrench className="w-5 h-5" /></div>
          <div className="font-semibold text-foreground">Log a ticket</div>
          <div className="text-xs text-muted-foreground">Report an issue on any of your sites — routes to preferred providers first.</div>
        </Link>
        <Link to="/find-providers" data-testid="dashboard-find-providers" className="bg-gradient-to-br from-primary/10 via-blue-500/5 to-transparent border border-primary/30 rounded-2xl p-5 hover:border-primary/60 transition-colors">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-blue-600 text-white flex items-center justify-center mb-3"><Users className="w-5 h-5" /></div>
          <div className="font-semibold text-foreground">Browse providers</div>
          <div className="text-xs text-muted-foreground">Filter verified commercial pros by trade, price, rating & credentials.</div>
        </Link>
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-foreground">Commercial sites</h2>
          <Link to="/post-job"><Button size="sm" variant="outline"><Wrench className="w-3.5 h-3.5 mr-1" /> Log ticket</Button></Link>
        </div>
        <div className="space-y-3">
          {mockSites.map((s) => (
            <div key={s.name} className="bg-card border border-border rounded-2xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-violet-500 to-primary text-white flex items-center justify-center"><Building2 className="w-5 h-5" /></div>
                  <div>
                    <div className="font-semibold text-foreground">{s.name}</div>
                    <div className="text-xs text-muted-foreground">{s.address}</div>
                    <div className="flex flex-wrap gap-2 mt-2">
                      <Badge variant="secondary" className="text-[10px]">SLA: {s.sla}</Badge>
                      <Badge className={s.compliance >= 95 ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'}>{s.compliance}% compliant</Badge>
                    </div>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-xs text-muted-foreground">Open</div>
                  <div className="text-xl font-bold text-foreground">{s.open_tickets}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-card border border-border rounded-2xl p-4">
      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className={`w-8 h-8 rounded-lg bg-muted/60 flex items-center justify-center ${color}`}><Icon className="w-4 h-4" /></div>
      </div>
      <div className="text-2xl font-bold text-foreground mt-2">{value}</div>
    </div>
  );
}
