import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Star, ShieldCheck, Zap, MapPin } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';
import { useAuth } from '../../context/AuthContext';

// Fix Leaflet default markers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const createIcon = (color) => L.divIcon({
  className: 'custom-marker',
  html: `<div style="background:${color};width:24px;height:24px;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.2);display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:bold;">✦</div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

export default function LiveMap() {
  const [providers, setProviders] = useState([]);
  const [selected, setSelected] = useState(null);
  const { user } = useAuth();

  useEffect(() => {
    api.get('/providers/nearby').then((r) => setProviders(r.data));
  }, []);

  const center = [-36.8485, 174.7633]; // Auckland
  const catColors = {
    plumbing: '#3B82F6',
    electrical: '#F59E0B',
    cleaning: '#10B981',
    lawn: '#22C55E',
    hvac: '#06B6D4',
    handyman: '#8B5CF6',
    painting: '#EC4899',
    roofing: '#F97316',
  };

  return (
    <div className="h-[calc(100vh-64px)] flex">
      <aside className="w-96 border-r border-border bg-card flex flex-col shrink-0 overflow-hidden">
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-primary" />
            <h1 className="font-bold text-foreground">Live Map</h1>
          </div>
          <p className="text-xs text-muted-foreground mt-1">{providers.filter((p) => p.online).length} pros online near you</p>
        </div>
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {providers.map((p) => (
            <button key={p.user_id} onClick={() => setSelected(p)} className={`w-full text-left p-3 border-b border-border hover:bg-accent transition-colors ${selected?.user_id === p.user_id ? 'bg-primary/5' : ''}`}>
              <div className="flex items-start gap-3">
                <div className="relative shrink-0">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-blue-600 text-white text-xs font-semibold flex items-center justify-center">{p.business_name.split(' ').map((s) => s[0]).slice(0, 2).join('')}</div>
                  {p.online && <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-emerald-500 ring-2 ring-card" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <div className="text-sm font-medium text-foreground truncate">{p.business_name}</div>
                    {p.verified && <ShieldCheck className="w-3 h-3 text-primary shrink-0" />}
                  </div>
                  <div className="text-xs text-muted-foreground capitalize">{p.categories?.[0]}</div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                    <span className="inline-flex items-center gap-0.5"><Star className="w-3 h-3 fill-amber-400 text-amber-400" />{p.rating}</span>
                    <span>· {p.jobs_completed} jobs</span>
                    <span className="ml-auto font-medium text-foreground">${p.hourly_rate}/hr</span>
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
        {user?.role !== 'provider' && (
          <div className="p-3 border-t border-border">
            <Button className="w-full" variant="destructive"><Zap className="w-4 h-4 mr-2" /> Emergency Dispatch</Button>
          </div>
        )}
      </aside>

      <div className="flex-1 relative">
        <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%' }} className="z-0">
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="© OpenStreetMap contributors" />
          {providers.map((p) => (
            <Marker key={p.user_id} position={[p.latitude || center[0], p.longitude || center[1]]} icon={createIcon(catColors[p.categories?.[0]] || '#3B82F6')} eventHandlers={{ click: () => setSelected(p) }}>
              <Popup>
                <div className="min-w-[200px]">
                  <div className="font-semibold text-sm">{p.business_name}</div>
                  <div className="text-xs text-gray-600 capitalize">{p.categories?.[0]}</div>
                  <div className="flex items-center gap-1 text-xs mt-1"><Star className="w-3 h-3 fill-amber-400 text-amber-400" /> {p.rating} · {p.jobs_completed} jobs</div>
                  <div className="text-sm font-bold mt-1">${p.hourly_rate}/hr</div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>

        {selected && (
          <div className="absolute bottom-4 left-4 right-4 md:right-auto md:w-96 bg-card border border-border rounded-2xl p-4 shadow-xl z-[400]">
            <div className="flex items-start gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-blue-600 text-white font-bold flex items-center justify-center">{selected.business_name.split(' ').map((s) => s[0]).slice(0, 2).join('')}</div>
              <div className="flex-1">
                <div className="font-semibold text-foreground flex items-center gap-1.5">{selected.business_name} {selected.verified && <ShieldCheck className="w-4 h-4 text-primary" />}</div>
                <div className="text-xs text-muted-foreground capitalize">{selected.categories?.join(' · ')}</div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                  <span className="inline-flex items-center gap-0.5"><Star className="w-3 h-3 fill-amber-400 text-amber-400" />{selected.rating} ({selected.reviews_count})</span>
                  <span>· {selected.jobs_completed} jobs done</span>
                </div>
              </div>
              <div className="text-lg font-bold text-primary">${selected.hourly_rate}<span className="text-xs text-muted-foreground font-normal">/hr</span></div>
            </div>
            <p className="text-sm text-muted-foreground mt-2">{selected.bio}</p>
            <div className="flex gap-2 mt-3">
              <Button className="flex-1" size="sm">Book Now</Button>
              <Button variant="outline" size="sm" className="flex-1">Message</Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
