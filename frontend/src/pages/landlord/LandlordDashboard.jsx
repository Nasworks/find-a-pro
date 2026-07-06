import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Home as HomeIcon, Users, Wrench, DollarSign, Plus, FileText, TrendingUp } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';

export default function LandlordDashboard() {
  const [properties, setProperties] = useState([]);

  useEffect(() => {
    api.get('/properties/mine')
      .then((r) => setProperties(r.data))
      .catch((err) => console.error('[Landlord] properties failed:', err));
  }, []);

  const tenantCount = properties.reduce((s, p) => s + (p.tenants?.length || 0), 0);
  const totalSpent = properties.reduce((s, p) => s + (p.total_spent || 0), 0);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase text-muted-foreground tracking-wider">Landlord Portal</div>
          <h1 className="text-2xl font-bold text-foreground">Manage your rentals</h1>
        </div>
        <Link to="/property/dashboard"><Button><Plus className="w-4 h-4 mr-1" /> Add Rental</Button></Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon={HomeIcon} label="Rentals" value={properties.length} color="text-orange-500" />
        <StatCard icon={Users} label="Tenants" value={tenantCount} color="text-primary" />
        <StatCard icon={Wrench} label="Maintenance jobs" value={properties.reduce((s, p) => s + (p.jobs_count || 0), 0)} color="text-violet-500" />
        <StatCard icon={DollarSign} label="Total spend" value={`$${totalSpent.toFixed(0)}`} color="text-emerald-500" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Link to="/post-job" className="bg-card border border-border rounded-2xl p-5 hover:border-primary/40 transition-colors">
          <div className="w-10 h-10 rounded-lg bg-primary text-white flex items-center justify-center mb-3"><Wrench className="w-5 h-5" /></div>
          <div className="font-semibold text-foreground">Request maintenance</div>
          <div className="text-xs text-muted-foreground">Post a job for one of your rentals — quotes in minutes.</div>
        </Link>
        <Link to="/insurance-history" className="bg-card border border-border rounded-2xl p-5 hover:border-primary/40 transition-colors">
          <div className="w-10 h-10 rounded-lg bg-teal-500 text-white flex items-center justify-center mb-3"><FileText className="w-5 h-5" /></div>
          <div className="font-semibold text-foreground">Property history</div>
          <div className="text-xs text-muted-foreground">Downloadable maintenance record for insurance & sale.</div>
        </Link>
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-foreground">Rental portfolio</h2>
          <Link to="/property/dashboard" className="text-sm text-primary hover:underline">View all →</Link>
        </div>
        {properties.length === 0 ? (
          <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
            <HomeIcon className="w-10 h-10 mx-auto text-muted-foreground mb-3 opacity-40" />
            <div className="font-medium text-foreground">No rentals yet</div>
            <p className="text-sm text-muted-foreground mt-1">Add your rental properties to track maintenance & tenants.</p>
            <Link to="/property/dashboard"><Button className="mt-4"><Plus className="w-4 h-4 mr-1" /> Add first rental</Button></Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {properties.map((p) => (
              <div key={p.property_id} className="bg-card border border-border rounded-2xl p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-semibold text-foreground">{p.address}</div>
                    <div className="text-xs text-muted-foreground capitalize">{p.property_type} · {p.bedrooms} bed</div>
                  </div>
                  <Badge variant="secondary">{p.tenants?.length || 0} tenant{(p.tenants?.length || 0) !== 1 ? 's' : ''}</Badge>
                </div>
                <div className="grid grid-cols-2 gap-2 mt-3 text-center text-xs">
                  <div className="p-2 rounded-lg bg-muted/40"><div className="text-muted-foreground">Jobs</div><div className="font-bold text-foreground">{p.jobs_count || 0}</div></div>
                  <div className="p-2 rounded-lg bg-muted/40"><div className="text-muted-foreground">Spend</div><div className="font-bold text-foreground">${p.total_spent || 0}</div></div>
                </div>
              </div>
            ))}
          </div>
        )}
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
