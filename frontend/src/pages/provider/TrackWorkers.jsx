import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Users, Battery, Wifi } from 'lucide-react';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';
import { SidePane } from '../../components/SidePane';

const createIcon = (color) => L.divIcon({
  className: 'worker-marker',
  html: `<div style="background:${color};width:32px;height:32px;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.2);display:flex;align-items:center;justify-content:center;color:white;font-size:12px;font-weight:bold;">W</div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

export default function TrackWorkers() {
  const [members, setMembers] = useState([]);
  const [devices, setDevices] = useState([]);

  useEffect(() => {
    api.get('/team')
      .then((r) => setMembers(r.data))
      .catch((err) => console.error('[TrackWorkers] team failed:', err));
    api.get('/gps-devices')
      .then((r) => setDevices(r.data))
      .catch((err) => console.error('[TrackWorkers] devices failed:', err));
  }, []);

  // Assign fake positions to members clustered around Auckland
  const center = [-36.8485, 174.7633];
  const withPositions = members.map((m, i) => ({
    ...m,
    lat: m.latitude || (-36.8485 + (Math.sin(i) * 0.02)),
    lng: m.longitude || (174.7633 + (Math.cos(i) * 0.03)),
  }));

  return (
    <div className="h-[calc(100dvh-136px)] lg:h-[calc(100vh-64px)] flex">
      <SidePane label="Workers" title="Team on the map" icon={Users} side="left" testid="workers-pane">
      <aside className="w-full lg:w-96 lg:border-r border-border bg-card flex flex-col shrink-0 overflow-hidden">
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-primary" />
            <h1 className="font-bold text-foreground">Track Workers</h1>
          </div>
          <p className="text-xs text-muted-foreground mt-1">{withPositions.filter((m) => m.status === 'on_job').length} on job · {withPositions.filter((m) => m.status === 'available').length} available</p>
        </div>
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {withPositions.length === 0 && (
            <div className="p-8 text-center text-sm text-muted-foreground">
              <Users className="w-8 h-8 mx-auto mb-2 opacity-40" />
              Add team members to track them on the map
            </div>
          )}
          {withPositions.map((m) => (
            <div key={m.member_id} className="p-3 border-b border-border">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-blue-600 text-white text-xs font-semibold flex items-center justify-center">
                    {m.name.split(' ').map((s) => s[0]).slice(0, 2).join('')}
                  </div>
                  <span className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full ring-2 ring-card ${m.status === 'on_job' ? 'bg-blue-500' : m.status === 'available' ? 'bg-emerald-500' : 'bg-gray-400'}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-foreground truncate">{m.name}</div>
                  <div className="text-xs text-muted-foreground">{m.role} · <span className="capitalize">{m.status.replace('_', ' ')}</span></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </aside>
      </SidePane>

      <div className="flex-1 relative min-w-0 isolate">
        <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%' }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="© OpenStreetMap contributors" />
          {withPositions.map((m) => (
            <Marker key={m.member_id} position={[m.lat, m.lng]} icon={createIcon(m.status === 'on_job' ? '#3B82F6' : m.status === 'available' ? '#10B981' : '#9CA3AF')}>
              <Popup>
                <div className="min-w-[180px]">
                  <div className="font-semibold text-sm">{m.name}</div>
                  <div className="text-xs text-gray-600">{m.role}</div>
                  <div className="text-xs mt-1 capitalize">Status: {m.status.replace('_', ' ')}</div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
