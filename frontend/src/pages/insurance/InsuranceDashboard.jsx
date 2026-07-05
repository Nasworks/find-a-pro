import React, { useEffect, useState } from 'react';
import { Shield, FileText, Building2, DollarSign, Wrench, ExternalLink, Search } from 'lucide-react';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import api from '../../lib/api';

const mockPortfolio = [
  { name: 'John Smith', address: '123 Queen Street, Auckland', jobs: 12, spent: 4850, since: '12/15/2025', access: 'Full Access' },
  { name: 'Sarah Johnson', address: '456 Victoria Avenue, Wellington', jobs: 8, spent: 2340, since: '11/20/2025', access: 'Full Access' },
  { name: 'Michael Chen', address: '789 Ponsonby Road, Auckland', jobs: 5, spent: 1650, since: '10/08/2025', access: 'Verified' },
];

export default function InsuranceDashboard() {
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState('properties');
  const [products, setProducts] = useState([]);

  useEffect(() => { api.get('/products').then((r) => setProducts(r.data.slice(0, 6))).catch(() => {}); }, []);

  const filtered = mockPortfolio.filter((p) => !query || p.name.toLowerCase().includes(query.toLowerCase()) || p.address.toLowerCase().includes(query.toLowerCase()));
  const totalJobs = mockPortfolio.reduce((s, p) => s + p.jobs, 0);
  const totalSpend = mockPortfolio.reduce((s, p) => s + p.spent, 0);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-teal-600 text-white flex items-center justify-center"><Shield className="w-5 h-5" /></div>
            <div>
              <div className="text-xs text-muted-foreground">Insurance Portal</div>
              <h1 className="text-xl font-bold text-foreground">Property & Document Access</h1>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon={Building2} label="Properties" value={mockPortfolio.length} color="text-teal-500" />
        <StatCard icon={FileText} label="Shared Docs" value="3" color="text-primary" />
        <StatCard icon={Wrench} label="Total Jobs" value={totalJobs} color="text-violet-500" />
        <StatCard icon={DollarSign} label="Total Spend" value={`$${totalSpend.toLocaleString()}`} color="text-emerald-500" />
      </div>

      <div className="border-b border-border">
        <div className="flex gap-1 -mb-px">
          <button onClick={() => setTab('properties')} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'properties' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>Properties ({mockPortfolio.length})</button>
          <button onClick={() => setTab('docs')} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'docs' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>Shared Docs (3)</button>
        </div>
      </div>

      {tab === 'properties' && (
        <div>
          <div className="relative max-w-lg mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search properties or clients..." className="w-full pl-10 pr-4 py-2 rounded-lg bg-muted/40 border border-transparent focus:border-primary/40 focus:bg-background outline-none text-sm" />
          </div>

          <div className="text-xs uppercase font-semibold text-muted-foreground mb-2">Properties with Shared Access</div>
          <div className="space-y-3">
            {filtered.map((p, i) => (
              <div key={i} className="bg-card border border-border rounded-2xl p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-teal-500 to-teal-600 text-white text-xs font-semibold flex items-center justify-center">{p.name.split(' ').map((s) => s[0]).join('')}</div>
                    <div>
                      <div className="font-semibold text-foreground">{p.name}</div>
                      <div className="text-xs text-muted-foreground flex items-center gap-1"><Building2 className="w-3 h-3" /> {p.address}</div>
                    </div>
                  </div>
                  <Badge className={p.access === 'Full Access' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'}>{p.access}</Badge>
                </div>
                <div className="flex flex-wrap items-center gap-4 mt-3 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1"><Wrench className="w-3 h-3" /> {p.jobs} jobs</span>
                  <span className="inline-flex items-center gap-1"><DollarSign className="w-3 h-3" /> ${p.spent}</span>
                  <span>Since {p.since}</span>
                </div>
                <Button variant="outline" size="sm" className="w-full mt-3"><ExternalLink className="w-3.5 h-3.5 mr-2" /> View Property History</Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'docs' && (
        <div className="space-y-3">
          {[
            { name: 'Property Inspection Report', client: 'John Smith', date: '2026-06-15' },
            { name: 'Roof Repair Certificate', client: 'Sarah Johnson', date: '2026-05-22' },
            { name: 'Electrical Compliance Cert', client: 'Michael Chen', date: '2026-04-10' },
          ].map((d, i) => (
            <div key={i} className="bg-card border border-border rounded-xl p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center"><FileText className="w-4 h-4" /></div>
                <div>
                  <div className="text-sm font-medium text-foreground">{d.name}</div>
                  <div className="text-xs text-muted-foreground">{d.client} · {d.date}</div>
                </div>
              </div>
              <Button variant="outline" size="sm">Download</Button>
            </div>
          ))}
        </div>
      )}
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
