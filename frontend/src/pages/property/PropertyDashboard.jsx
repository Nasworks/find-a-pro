import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Building2, MapPin, DollarSign, Users, Wrench, Trash2, TrendingUp } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import api from '../../lib/api';
import { toast } from 'sonner';

export default function PropertyDashboard() {
  const [properties, setProperties] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ address: '', property_type: 'residential', bedrooms: '', size: '' });

  const load = () => api.get('/properties/mine').then((r) => setProperties(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const addProp = async () => {
    if (!form.address) return;
    await api.post('/properties', { ...form, bedrooms: form.bedrooms ? Number(form.bedrooms) : null });
    toast.success('Property added');
    setOpen(false);
    setForm({ address: '', property_type: 'residential', bedrooms: '', size: '' });
    load();
  };

  const removeProp = async (id) => {
    await api.delete(`/properties/${id}`);
    toast.success('Property removed');
    load();
  };

  const totalJobs = properties.reduce((s, p) => s + (p.jobs_count || 0), 0);
  const totalSpend = properties.reduce((s, p) => s + (p.total_spent || 0), 0);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Property Portfolio</h1>
          <p className="text-sm text-muted-foreground">Manage your properties, tenants & maintenance</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild><Button><Plus className="w-4 h-4 mr-1" /> Add Property</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Add a property</DialogTitle></DialogHeader>
            <div className="space-y-3 mt-2">
              <div><Label>Address</Label><Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="e.g. 123 Queen St, Auckland" className="mt-1.5" /></div>
              <div><Label>Type</Label>
                <Select value={form.property_type} onValueChange={(v) => setForm({ ...form, property_type: v })}>
                  <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="residential">Residential</SelectItem>
                    <SelectItem value="commercial">Commercial</SelectItem>
                    <SelectItem value="rental">Rental</SelectItem>
                    <SelectItem value="mixed">Mixed use</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><Label>Bedrooms</Label><Input type="number" value={form.bedrooms} onChange={(e) => setForm({ ...form, bedrooms: e.target.value })} placeholder="3" className="mt-1.5" /></div>
                <div><Label>Size</Label><Input value={form.size} onChange={(e) => setForm({ ...form, size: e.target.value })} placeholder="150 sqm" className="mt-1.5" /></div>
              </div>
              <Button onClick={addProp} className="w-full">Add Property</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon={Building2} label="Properties" value={properties.length} color="text-violet-500" />
        <StatCard icon={Wrench} label="Total Jobs" value={totalJobs} color="text-primary" />
        <StatCard icon={DollarSign} label="Total Spend" value={`$${totalSpend.toFixed(0)}`} color="text-emerald-500" />
        <StatCard icon={Users} label="Active Tenants" value={properties.reduce((s, p) => s + (p.tenants?.length || 0), 0)} color="text-amber-500" />
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-foreground">Your Properties</h2>
          <Link to="/marketplace" className="text-sm text-primary hover:underline">Order supplies →</Link>
        </div>
        {properties.length === 0 ? (
          <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
            <Building2 className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
            <div className="text-lg font-medium text-foreground">No properties yet</div>
            <p className="text-sm text-muted-foreground mt-1">Add your first property to get started.</p>
            <Button onClick={() => setOpen(true)} className="mt-4"><Plus className="w-4 h-4 mr-1" /> Add Property</Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {properties.map((p) => (
              <div key={p.property_id} className="bg-card border border-border rounded-2xl p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-violet-500 to-violet-600 text-white flex items-center justify-center"><Building2 className="w-5 h-5" /></div>
                    <div>
                      <div className="font-semibold text-foreground">{p.address}</div>
                      <div className="text-xs text-muted-foreground capitalize">{p.property_type}{p.bedrooms ? ` · ${p.bedrooms} bed` : ''}{p.size ? ` · ${p.size}` : ''}</div>
                    </div>
                  </div>
                  <button onClick={() => removeProp(p.property_id)} className="p-1.5 text-muted-foreground hover:text-destructive rounded-lg hover:bg-destructive/10 transition-colors"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
                <div className="grid grid-cols-3 gap-2 mt-4 text-center">
                  <div className="p-2 rounded-lg bg-muted/40">
                    <div className="text-xs text-muted-foreground">Jobs</div>
                    <div className="font-bold text-foreground">{p.jobs_count || 0}</div>
                  </div>
                  <div className="p-2 rounded-lg bg-muted/40">
                    <div className="text-xs text-muted-foreground">Spent</div>
                    <div className="font-bold text-foreground">${p.total_spent || 0}</div>
                  </div>
                  <div className="p-2 rounded-lg bg-muted/40">
                    <div className="text-xs text-muted-foreground">Tenants</div>
                    <div className="font-bold text-foreground">{p.tenants?.length || 0}</div>
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  <Link to="/post-job" className="flex-1"><Button variant="outline" size="sm" className="w-full"><Wrench className="w-3.5 h-3.5 mr-1" /> Request Service</Button></Link>
                  <Button variant="outline" size="sm" className="flex-1"><Users className="w-3.5 h-3.5 mr-1" /> Add Tenant</Button>
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
