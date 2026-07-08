import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Heart, Star, Shield, MapPin, Loader2, Search, HeartOff } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';
import { toast } from 'sonner';

const AVATAR_COLORS = ['bg-emerald-500', 'bg-blue-500', 'bg-violet-500', 'bg-amber-500', 'bg-rose-500', 'bg-teal-500', 'bg-orange-500'];

export default function SavedProviders() {
  const navigate = useNavigate();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    api.get('/saved-providers')
      .then((r) => setResults(r.data.results || []))
      .catch(() => toast.error('Could not load saved providers'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const unsave = async (providerId) => {
    const prev = results;
    setResults((rs) => rs.filter((p) => p.user_id !== providerId));
    try {
      await api.delete(`/saved-providers/${providerId}`);
      toast.success('Removed from Saved Pros');
    } catch {
      setResults(prev);
      toast.error('Failed to remove');
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-6" data-testid="saved-providers-page">
      <div className="mb-4 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-500 to-pink-600 text-white flex items-center justify-center">
          <Heart className="w-5 h-5 fill-white" />
        </div>
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">Saved Pros</h1>
          <p className="text-sm text-muted-foreground">Your shortlisted providers — hire them again or invite to a new job.</p>
        </div>
        <div className="ml-auto text-sm text-muted-foreground" data-testid="saved-providers-count">
          {loading ? '…' : `${results.length} saved`}
        </div>
      </div>

      {loading ? (
        <div className="py-16 flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
      ) : results.length === 0 ? (
        <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center" data-testid="saved-providers-empty">
          <Heart className="w-8 h-8 mx-auto text-muted-foreground opacity-40 mb-2" />
          <div className="font-medium text-foreground">No saved pros yet</div>
          <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">Tap the heart on any provider profile to save them here for quick access next time.</p>
          <Button onClick={() => navigate('/find-providers')} className="mt-4" data-testid="saved-providers-browse-btn">
            <Search className="w-4 h-4 mr-1.5" /> Browse Providers
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {results.map((p) => <SavedProviderCard key={p.user_id} p={p} onOpen={() => navigate(`/providers/${p.user_id}`)} onUnsave={() => unsave(p.user_id)} />)}
        </div>
      )}
    </div>
  );
}

function SavedProviderCard({ p, onOpen, onUnsave }) {
  const initials = (p.business_name || 'P').split(' ').slice(0, 2).map((s) => s[0]).join('').toUpperCase();
  const avatarColor = AVATAR_COLORS[(p.user_id || '').charCodeAt(0) % AVATAR_COLORS.length];
  return (
    <div
      data-testid={`saved-provider-card-${p.user_id}`}
      className="relative bg-card border border-border rounded-2xl p-4 hover:border-primary/40 hover:shadow-md hover:shadow-primary/5 transition-all group"
    >
      <button
        data-testid={`unsave-provider-${p.user_id}`}
        onClick={(e) => { e.stopPropagation(); onUnsave(); }}
        className="absolute top-3 right-3 w-8 h-8 rounded-full bg-rose-500/10 text-rose-500 hover:bg-rose-500/20 flex items-center justify-center transition-colors"
        aria-label="Remove from saved"
        title="Remove from saved"
      >
        <HeartOff className="w-4 h-4" />
      </button>
      <button className="text-left w-full" onClick={onOpen}>
        <div className="flex items-start gap-3 pr-8">
          <div className={`w-12 h-12 rounded-full ${avatarColor} text-white font-bold flex items-center justify-center relative shrink-0`}>
            {initials}
            {p.verified && (
              <span className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-primary text-white border-2 border-card flex items-center justify-center">
                <Shield className="w-2 h-2" />
              </span>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-1">
              <div className="font-semibold text-foreground truncate group-hover:text-primary transition-colors">{p.business_name}</div>
              <div className="flex items-center gap-0.5 text-xs font-bold text-amber-500 shrink-0">
                <Star className="w-3.5 h-3.5 fill-amber-500" /> {p.rating?.toFixed?.(1) ?? '—'}
              </div>
            </div>
            <div className="text-xs text-muted-foreground truncate">{p.categories?.join(', ')}</div>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-1">
          {p.verified && <Badge className="text-[10px] bg-blue-500/10 text-blue-600 border-transparent">ID</Badge>}
          {p.insured && <Badge className="text-[10px] bg-emerald-500/10 text-emerald-600 border-transparent">Insured</Badge>}
          {p.background_checked && <Badge className="text-[10px] bg-amber-500/10 text-amber-600 border-transparent">BG Check</Badge>}
          {p.accredited && <Badge className="text-[10px] bg-violet-500/10 text-violet-600 border-transparent">Accredited</Badge>}
        </div>
        {p.bio && <p className="mt-3 text-xs text-muted-foreground line-clamp-2">{p.bio}</p>}
        <div className="mt-3 pt-3 border-t border-border flex items-center justify-between text-xs">
          <span className="inline-flex items-center gap-1 text-muted-foreground"><MapPin className="w-3 h-3" /> Auckland</span>
          <span className="font-bold text-foreground">${p.hourly_rate?.toFixed?.(0)}/hr</span>
        </div>
      </button>
    </div>
  );
}
