import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Star, MapPin, Shield, ShieldCheck, Award, Clock, Briefcase, MessageSquare, Loader2, CheckCircle2, Sparkles, Heart } from 'lucide-react';
import { Button } from '../../components/ui/button';
import CredentialTicks from '../../components/CredentialTicks';
import SpecializationBadges from '../../components/SpecializationBadges';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';
import { toast } from 'sonner';

const AVATAR_COLORS = ['bg-emerald-500', 'bg-blue-500', 'bg-violet-500', 'bg-amber-500', 'bg-rose-500', 'bg-teal-500'];

export default function ProviderProfile() {
  const { providerId } = useParams();
  const navigate = useNavigate();
  const [p, setP] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.get(`/providers/${providerId}`)
      .then((r) => setP(r.data))
      .catch(() => toast.error('Provider not found'))
      .finally(() => setLoading(false));
  }, [providerId]);

  if (loading) return <div className="py-24 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>;
  if (!p) return null;

  const initials = (p.business_name || 'P').split(' ').slice(0, 2).map((s) => s[0]).join('').toUpperCase();
  const avatarColor = AVATAR_COLORS[(p.user_id || '').charCodeAt(0) % AVATAR_COLORS.length];

  const startChat = async () => {
    try {
      await api.post('/messages', { to_user_id: p.user_id, body: `Hi ${p.business_name}, I found your profile on Pro Finder NZ and would like to discuss a job.` });
      toast.success('Message sent');
      navigate('/messages');
    } catch { toast.error('Failed to send'); }
  };

  const toggleSave = async () => {
    if (saving) return;
    setSaving(true);
    const nextSaved = !p.is_saved;
    setP((cur) => ({ ...cur, is_saved: nextSaved }));
    try {
      if (nextSaved) {
        await api.post(`/saved-providers/${p.user_id}`);
        toast.success(`Saved ${p.business_name}`);
      } else {
        await api.delete(`/saved-providers/${p.user_id}`);
        toast.success('Removed from Saved Pros');
      }
    } catch {
      setP((cur) => ({ ...cur, is_saved: !nextSaved }));
      toast.error('Could not update Saved Pros');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-4 md:p-6" data-testid="provider-profile-page">
      <button onClick={() => navigate(-1)} data-testid="provider-back" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      {/* Hero */}
      <div className="bg-card border border-border rounded-2xl p-6 flex flex-col md:flex-row items-start gap-6">
        <div className={`w-24 h-24 rounded-2xl ${avatarColor} text-white text-3xl font-bold flex items-center justify-center relative shrink-0`}>
          {initials}
          {p.verified && (
            <span className="absolute -bottom-1 -right-1 w-7 h-7 rounded-full bg-primary text-white border-2 border-card flex items-center justify-center">
              <Shield className="w-3.5 h-3.5" />
            </span>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl md:text-3xl font-bold text-foreground" data-testid="provider-name">{p.business_name}</h1>
          <CredentialTicks providerId={providerId} className="mt-2" />
          <div className="mt-2"><SpecializationBadges providerId={providerId} compact /></div>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-sm">
            <span className="inline-flex items-center gap-1 font-bold text-amber-500"><Star className="w-4 h-4 fill-amber-500" /> {p.rating?.toFixed?.(1) ?? '—'}</span>
            <span className="text-muted-foreground">·</span>
            <span className="text-muted-foreground">{p.reviews_count ?? 0} reviews</span>
            <span className="text-muted-foreground">·</span>
            <span className="inline-flex items-center gap-1 text-muted-foreground"><Briefcase className="w-3.5 h-3.5" /> {p.jobs_completed ?? 0} jobs done</span>
            <span className="text-muted-foreground">·</span>
            <span className="inline-flex items-center gap-1 text-muted-foreground"><MapPin className="w-3.5 h-3.5" /> Auckland</span>
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {p.verified && <Badge className="bg-blue-500/10 text-blue-600 border-transparent"><Shield className="w-3 h-3 mr-1" /> ID Verified</Badge>}
            {p.insured && <Badge className="bg-emerald-500/10 text-emerald-600 border-transparent"><CheckCircle2 className="w-3 h-3 mr-1" /> Insured</Badge>}
            {p.background_checked && <Badge className="bg-amber-500/10 text-amber-600 border-transparent"><ShieldCheck className="w-3 h-3 mr-1" /> Background checked</Badge>}
            {p.accredited && <Badge className="bg-violet-500/10 text-violet-600 border-transparent"><Award className="w-3 h-3 mr-1" /> Accredited</Badge>}
            {p.response_time_hours && <Badge className="bg-muted text-muted-foreground border-transparent"><Clock className="w-3 h-3 mr-1" /> Responds in ~{p.response_time_hours}h</Badge>}
          </div>
        </div>
        <div className="w-full md:w-auto flex flex-col gap-2 md:items-end">
          <div className="text-xs text-muted-foreground">Hourly rate</div>
          <div className="text-3xl font-bold text-foreground">${p.hourly_rate?.toFixed?.(0)}<span className="text-sm text-muted-foreground font-medium">/hr</span></div>
          <Button data-testid="provider-message-btn" onClick={startChat} className="w-full md:w-auto"><MessageSquare className="w-4 h-4 mr-1.5" /> Message</Button>
          <Button data-testid="provider-invite-btn" variant="outline" onClick={() => navigate('/post-job', { state: { assignedProviderName: p.business_name } })} className="w-full md:w-auto"><Sparkles className="w-4 h-4 mr-1.5" /> Invite to job</Button>
          <Button
            data-testid="provider-save-btn"
            variant="outline"
            onClick={toggleSave}
            disabled={saving}
            aria-pressed={!!p.is_saved}
            className={`w-full md:w-auto ${p.is_saved ? 'text-rose-500 border-rose-500/40 hover:bg-rose-500/10' : ''}`}
          >
            <Heart className={`w-4 h-4 mr-1.5 ${p.is_saved ? 'fill-rose-500' : ''}`} />
            {p.is_saved ? 'Saved' : 'Save Pro'}
          </Button>
        </div>
      </div>

      {/* About */}
      {p.bio && (
        <section className="mt-6 bg-card border border-border rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-foreground mb-2">About</h2>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">{p.bio}</p>
          {p.years_in_business && <p className="mt-3 text-xs text-muted-foreground"><Clock className="w-3 h-3 inline mr-1" /> {p.years_in_business}+ years in business</p>}
        </section>
      )}

      {/* Services */}
      {p.categories?.length > 0 && (
        <section className="mt-6 bg-card border border-border rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-foreground mb-3">Services</h2>
          <div className="flex flex-wrap gap-1.5">
            {p.categories.map((c) => <Badge key={c} className="bg-primary/10 text-primary border-primary/20">{c}</Badge>)}
          </div>
        </section>
      )}

      {/* Gallery */}
      {p.gallery?.length > 0 && (
        <section className="mt-6 bg-card border border-border rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-foreground mb-3">Past Work</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {p.gallery.map((src, i) => (
              <div key={i} className="aspect-square rounded-xl overflow-hidden bg-muted">
                <img src={src} alt={`Past work ${i + 1}`} className="w-full h-full object-cover hover:scale-105 transition-transform" loading="lazy" />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Reviews */}
      <section className="mt-6 bg-card border border-border rounded-2xl p-6" data-testid="provider-reviews">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-foreground">Reviews</h2>
          <div className="inline-flex items-center gap-1 text-amber-500 font-bold"><Star className="w-4 h-4 fill-amber-500" /> {p.rating?.toFixed?.(1)} · {p.reviews_count} total</div>
        </div>
        {p.reviews?.length === 0 ? (
          <p className="text-sm text-muted-foreground">No reviews yet.</p>
        ) : (
          <div className="space-y-3">
            {p.reviews.map((r) => (
              <div key={r.review_id} className="border-b border-border pb-3 last:border-b-0 last:pb-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-foreground text-sm">{r.author_name}</span>
                  <span className="inline-flex items-center gap-0.5 text-amber-500 text-xs font-bold">
                    {[...Array(5)].map((_, i) => <Star key={i} className={`w-3 h-3 ${i < r.rating ? 'fill-amber-500' : ''}`} />)}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">{r.text}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
