import React from 'react';
import { Home as HomeIcon, Check, MapPin, Star } from 'lucide-react';
import { Input } from './ui/input';
import AddressAutocomplete from './AddressAutocomplete';

/**
 * Location for a job: pick a saved property, or search an address (with optional save-to-profile).
 * value: { property_id, address, lat, lng, save, save_name }
 */
export default function JobLocationPicker({ properties, value, onChange, onPickProperty, canSave = true }) {
  const usingNew = !value.property_id;
  // functional update: typing fires onChange + onSelect back-to-back, so never spread a stale value
  const set = (patch) => onChange((v) => ({ ...v, ...patch }));

  return (
    <div className="space-y-2" data-testid="job-location-picker">
      {properties.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {properties.map((p) => {
            const active = value.property_id === p.property_id;
            const Icon = HomeIcon;
            return (
              <button
                key={p.property_id}
                type="button"
                data-testid={`job-location-property-${p.property_id}`}
                onClick={() => onPickProperty(p)}
                aria-pressed={active}
                className={`relative min-w-0 w-full flex items-start gap-2.5 p-3 rounded-xl border-2 text-left transition-colors ${active ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}
              >
                <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${active ? 'text-primary' : 'text-muted-foreground'}`} />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-1 text-sm font-semibold text-foreground truncate">
                    {p.name || (p.is_primary ? 'Main property' : 'Property')}
                    {p.is_primary && <Star className="w-3 h-3 text-amber-500 shrink-0" />}
                  </span>
                  <span className="block text-xs text-muted-foreground truncate">{p.address}</span>
                </span>
                {active && <Check className="w-4 h-4 text-primary shrink-0" />}
              </button>
            );
          })}
          <button
            type="button"
            data-testid="job-location-new"
            onClick={() => onChange({ property_id: null, address: '', lat: null, lng: null, save: true, save_name: '' })}
            aria-pressed={usingNew}
            className={`min-w-0 w-full flex items-center gap-2.5 p-3 rounded-xl border-2 text-left transition-colors ${usingNew ? 'border-primary bg-primary/5' : 'border-dashed border-border hover:border-primary/40'}`}
          >
            <MapPin className={`w-4 h-4 shrink-0 ${usingNew ? 'text-primary' : 'text-muted-foreground'}`} />
            <span className="text-sm font-medium text-foreground">Search another address</span>
          </button>
        </div>
      )}

      {usingNew && (
        <div className="space-y-2 pt-1">
          <AddressAutocomplete
            testid="post-job-location"
            value={value.address}
            onChange={(v) => set({ address: v })}
            onSelect={(p) => set(p ? { address: p.address, lat: p.lat, lng: p.lng } : { lat: null, lng: null })}
            placeholder="Search property or address"
          />
          {canSave && <label className="flex items-center gap-2 text-sm text-foreground cursor-pointer">
            <input type="checkbox" data-testid="job-location-save" checked={!!value.save} onChange={(e) => set({ save: e.target.checked })} className="w-4 h-4 accent-[hsl(var(--primary))]" />
            Save to my properties
          </label>}
          {canSave && value.save && (
            <Input data-testid="job-location-save-name" value={value.save_name || ''} onChange={(e) => set({ save_name: e.target.value })} placeholder={properties.length ? 'Name, e.g. "Rental – Ponsonby" (optional)' : 'Name, e.g. "Home" (optional)'} maxLength={60} />
          )}
        </div>
      )}
    </div>
  );
}
