import React, { useEffect, useState } from 'react';
import { Loader2, Star } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import AddressAutocomplete from './AddressAutocomplete';
import api from '../lib/api';
import { toast } from 'sonner';

const EMPTY = { name: '', address: '', property_type: 'residential', bedrooms: '', bathrooms: '', access_notes: '', lat: null, lng: null, is_primary: false };

/** Add or edit a saved property. Props: open, onOpenChange, property (to edit), onSaved(prop), isFirst */
export default function PropertyFormDialog({ open, onOpenChange, property, onSaved, isFirst = false }) {
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const editing = !!property;

  useEffect(() => {
    if (!open) return;
    setForm(property ? {
      ...EMPTY, ...property,
      name: property.name || '', access_notes: property.access_notes || '',
      bedrooms: property.bedrooms ?? '', bathrooms: property.bathrooms ?? '',
    } : { ...EMPTY, is_primary: isFirst });
  }, [open, property, isFirst]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async (e) => {
    e.preventDefault();
    if (!form.address.trim()) { toast.error('Please enter an address'); return; }
    setSaving(true);
    const payload = {
      name: form.name.trim() || null,
      address: form.address.trim(),
      property_type: 'residential',
      bedrooms: form.bedrooms === '' ? null : Number(form.bedrooms),
      bathrooms: form.bathrooms === '' ? null : Number(form.bathrooms),
      access_notes: form.access_notes.trim() || null,
      lat: form.lat, lng: form.lng,
    };
    try {
      let res;
      if (editing) {
        res = await api.patch(`/properties/${property.property_id}`, payload);
        if (form.is_primary && !property.is_primary) await api.post(`/properties/${property.property_id}/primary`);
      } else {
        res = await api.post('/properties', { ...payload, is_primary: form.is_primary });
      }
      toast.success(editing ? 'Property updated' : 'Property saved');
      onSaved?.(res.data);
      onOpenChange(false);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not save property');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="property-form-dialog">
        <DialogHeader>
          <DialogTitle>{editing ? 'Edit property' : 'Add a property'}</DialogTitle>
          <DialogDescription>Saved properties can be picked in one tap when you post a job.</DialogDescription>
        </DialogHeader>
        <form onSubmit={save} className="space-y-4">
          <div>
            <Label>Name</Label>
            <Input data-testid="property-name" value={form.name} onChange={(e) => set('name', e.target.value)} placeholder='e.g. "Home" or "Rental – Ponsonby"' className="mt-1.5" maxLength={60} />
          </div>
          <div>
            <Label>Address</Label>
            <div className="mt-1.5">
              <AddressAutocomplete
                testid="property-address"
                value={form.address}
                onChange={(v) => set('address', v)}
                onSelect={(p) => setForm((f) => ({ ...f, lat: p?.lat ?? null, lng: p?.lng ?? null }))}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Bedrooms</Label>
              <Input data-testid="property-bedrooms" type="number" min="0" max="100" value={form.bedrooms} onChange={(e) => set('bedrooms', e.target.value)} className="mt-1.5" placeholder="—" />
            </div>
            <div>
              <Label>Bathrooms</Label>
              <Input data-testid="property-bathrooms" type="number" min="0" max="100" step="0.5" value={form.bathrooms} onChange={(e) => set('bathrooms', e.target.value)} className="mt-1.5" placeholder="—" />
            </div>
          </div>
          <div>
            <Label>Access notes <span className="text-muted-foreground font-normal">(only shown to the pro you hire)</span></Label>
            <Textarea data-testid="property-access-notes" value={form.access_notes} onChange={(e) => set('access_notes', e.target.value)} rows={2} placeholder="Gate codes, pets, parking…" className="mt-1.5" maxLength={500} />
          </div>
          {!(editing && property.is_primary) && (
            <label className="flex items-center gap-2 text-sm text-foreground cursor-pointer">
              <input type="checkbox" data-testid="property-is-primary" checked={form.is_primary} onChange={(e) => set('is_primary', e.target.checked)} className="w-4 h-4 accent-[hsl(var(--primary))]" />
              <Star className="w-3.5 h-3.5 text-amber-500" /> Make this my main property
            </label>
          )}
          <div className="flex gap-2 pt-1">
            <Button type="button" variant="outline" className="flex-1" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" data-testid="property-save" className="flex-1" disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : editing ? 'Save changes' : 'Save property'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
