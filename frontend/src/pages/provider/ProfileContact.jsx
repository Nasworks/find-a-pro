import React, { useState } from 'react';
import { User, Mail, Phone, MapPin, Save, Camera } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'sonner';
import api from '../../lib/api';

export default function ProfileContact() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({
    name: user?.name || '',
    email: user?.email || '',
    phone: user?.phone || '',
    city: user?.city || 'Auckland',
    bio: '',
    business_name: user?.name || '',
  });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await api.patch('/providers/me', { business_name: form.business_name, bio: form.bio });
      setUser({ ...user, ...form });
      toast.success('Profile saved');
    } catch (err) {
      console.error('[ProfileContact] save failed:', err);
      toast.error('Failed to save');
    } finally { setSaving(false); }
  };

  const initials = (form.name || 'U').split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase();

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Profile & Contact</h1>
        <p className="text-sm text-muted-foreground">This is what customers see on your provider profile</p>
      </div>

      <div className="bg-card border border-border rounded-2xl p-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="relative">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-blue-600 text-white text-2xl font-bold flex items-center justify-center">{initials}</div>
            <button className="absolute -bottom-1 -right-1 w-7 h-7 rounded-full bg-primary text-white flex items-center justify-center shadow-sm"><Camera className="w-3.5 h-3.5" /></button>
          </div>
          <div>
            <div className="font-semibold text-foreground text-lg">{form.business_name}</div>
            <div className="text-sm text-muted-foreground">Provider · {form.city}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label>Business name</Label>
            <Input value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} className="mt-1.5" />
          </div>
          <div>
            <Label>Your name</Label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1.5" />
          </div>
          <div>
            <Label>Email</Label>
            <div className="relative mt-1.5"><Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" /><Input type="email" value={form.email} readOnly className="pl-9" /></div>
          </div>
          <div>
            <Label>Phone</Label>
            <div className="relative mt-1.5"><Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" /><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="021 XXX XXXX" className="pl-9" /></div>
          </div>
          <div className="md:col-span-2">
            <Label>City</Label>
            <div className="relative mt-1.5"><MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" /><Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} className="pl-9" /></div>
          </div>
          <div className="md:col-span-2">
            <Label>About your business</Label>
            <Textarea rows={4} value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} placeholder="Tell customers about your experience, specialities, and what makes you different." className="mt-1.5" />
          </div>
        </div>

        <Button onClick={save} disabled={saving} className="mt-6"><Save className="w-4 h-4 mr-2" /> {saving ? 'Saving...' : 'Save changes'}</Button>
      </div>
    </div>
  );
}
