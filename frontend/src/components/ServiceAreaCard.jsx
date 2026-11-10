import React, { useEffect, useState } from 'react';
import { Navigation, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Slider } from './ui/slider';
import { Switch } from './ui/switch';
import { Button } from './ui/button';
import api from '../lib/api';

export const ServiceAreaCard = () => {
  const [limit, setLimit] = useState(false);
  const [km, setKm] = useState(25);
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api.get('/providers/me').then(({ data }) => {
      if (data.service_radius_km) { setLimit(true); setKm(data.service_radius_km); }
    }).catch(() => {}).finally(() => setLoaded(true));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await api.patch('/providers/me', { service_radius_km: limit ? km : null });
      toast.success(limit ? `You'll only show to customers within ${km} km` : 'You now show to customers at any distance');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not save');
    } finally { setSaving(false); }
  };

  if (!loaded) return null;
  return (
    <div className="bg-card border border-border rounded-2xl p-5" data-testid="service-area-card">
      <div className="flex items-center gap-2">
        <Navigation className="w-4 h-4 text-primary" />
        <div className="font-semibold text-foreground">Service area</div>
        <Switch checked={limit} onCheckedChange={setLimit} className="ml-auto" data-testid="service-area-toggle" />
      </div>
      <p className="text-xs text-muted-foreground mt-1">How far you'll travel from Auckland CBD. Customers further away won't see you in Find Providers.</p>
      {limit ? (
        <div className="mt-4">
          <div className="text-2xl font-bold tabular-nums" data-testid="service-area-value">{km} km</div>
          <Slider className="mt-3" min={1} max={200} step={1} value={[km]} onValueChange={([v]) => setKm(v)} data-testid="service-area-slider" />
          <div className="flex justify-between text-[10px] text-muted-foreground mt-1.5"><span>1 km</span><span>100 km</span><span>200 km</span></div>
        </div>
      ) : (
        <div className="mt-4 text-sm text-muted-foreground" data-testid="service-area-unlimited">No limit — you appear to every customer.</div>
      )}
      <Button onClick={save} disabled={saving} className="mt-4" size="sm" data-testid="service-area-save">
        {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />} Save service area
      </Button>
    </div>
  );
};

export default ServiceAreaCard;
