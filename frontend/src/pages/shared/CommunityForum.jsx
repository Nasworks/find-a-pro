import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MessageCircle, Eye, ArrowUp, ArrowDown, Clock, Search, Plus, Flame, Sparkles, TrendingUp, ShieldCheck, Users, Pin, X, Loader2, Tag as TagIcon, Send } from 'lucide-react';
import * as LucideIcons from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { toast } from 'sonner';
import api from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import { extractError } from '../../lib/errors';

const SORT_TABS = [
  { id: 'hot', label: 'Hot', icon: Flame },
  { id: 'new', label: 'New', icon: Sparkles },
  { id: 'top', label: 'Top', icon: TrendingUp },
];

function timeAgo(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  if (s < 604800) return `${Math.floor(s / 86400)}d ago`;
  return `${Math.floor(s / 604800)}w ago`;
}

function roleBadge(role) {
  const map = {
    provider: { label: 'Pro', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300' },
    customer: { label: 'Homeowner', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300' },
    landlord: { label: 'Landlord', cls: 'bg-orange-100 text-orange-700 dark:bg-orange-950/60 dark:text-orange-300' },
    property: { label: 'Property Mgr', cls: 'bg-violet-100 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300' },
    facilities: { label: 'Facilities', cls: 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-200' },
    insurance: { label: 'Insurance', cls: 'bg-teal-100 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300' },
  };
  return map[role] || map.customer;
}

function VoteControl({ score, userVote, onVote, size = 'md', testId }) {
  const iconSize = size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4';
  const btnSize = size === 'sm' ? 'w-6 h-6' : 'w-7 h-7';
  const numSize = size === 'sm' ? 'text-xs' : 'text-sm';
  return (
    <div className="flex flex-col items-center gap-0.5 shrink-0" onClick={(e) => e.stopPropagation()}>
      <button
        data-testid={testId ? `${testId}-upvote` : undefined}
        onClick={() => onVote(userVote === 1 ? 0 : 1)}
        className={`${btnSize} rounded-md flex items-center justify-center transition-colors ${userVote === 1 ? 'text-orange-500 bg-orange-500/10' : 'text-muted-foreground hover:text-orange-500 hover:bg-orange-500/10'}`}
        aria-label="Upvote"
      >
        <ArrowUp className={iconSize} />
      </button>
      <span className={`${numSize} font-bold tabular-nums ${userVote === 1 ? 'text-orange-500' : userVote === -1 ? 'text-blue-500' : 'text-foreground'}`}>{score}</span>
      <button
        data-testid={testId ? `${testId}-downvote` : undefined}
        onClick={() => onVote(userVote === -1 ? 0 : -1)}
        className={`${btnSize} rounded-md flex items-center justify-center transition-colors ${userVote === -1 ? 'text-blue-500 bg-blue-500/10' : 'text-muted-foreground hover:text-blue-500 hover:bg-blue-500/10'}`}
        aria-label="Downvote"
      >
        <ArrowDown className={iconSize} />
      </button>
    </div>
  );
}

function CategoryIcon({ icon, color, className = 'w-4 h-4' }) {
  const Icon = LucideIcons[icon] || LucideIcons.Hash;
  return (
    <div className={`rounded-md flex items-center justify-center text-white shrink-0`} style={{ backgroundColor: color, width: 28, height: 28 }}>
      <Icon className={className} />
    </div>
  );
}

export default function CommunityForum() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [audience, setAudience] = useState('customer');
  const [activeCat, setActiveCat] = useState('all');
  const [sort, setSort] = useState('hot');
  const [q, setQ] = useState('');
  const [posts, setPosts] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: '', body: '', category: '', tags: '' });

  const loadCategories = useCallback(() => {
    api.get('/forum/categories').then((r) => {
      setCategories(r.data.categories);
      setAudience(r.data.audience);
    }).catch((err) => console.error('[Forum] categories:', err));
    api.get('/forum/stats').then((r) => setStats(r.data)).catch(() => {});
  }, []);

  const loadPosts = useCallback(() => {
    setLoading(true);
    const params = { sort };
    if (activeCat && activeCat !== 'all') params.category = activeCat;
    if (q.trim()) params.q = q.trim();
    api.get('/forum/posts', { params })
      .then((r) => setPosts(r.data))
      .catch((err) => console.error('[Forum] posts:', err))
      .finally(() => setLoading(false));
  }, [sort, activeCat, q]);

  useEffect(() => { loadCategories(); }, [loadCategories]);
  useEffect(() => { loadPosts(); }, [loadPosts]);

  const handleVote = async (postId, value) => {
    // Optimistic
    setPosts((prev) => prev.map((p) => {
      if (p.post_id !== postId) return p;
      const prev_v = p.user_vote || 0;
      const delta = value - prev_v;
      return { ...p, user_vote: value, score: (p.score || 0) + delta };
    }));
    try {
      await api.post(`/forum/posts/${postId}/vote`, { value });
    } catch (err) {
      toast.error(extractError(err, 'Vote failed'));
      loadPosts();
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.category) return toast.error('Pick a category');
    setCreating(true);
    try {
      const tags = form.tags.split(',').map((t) => t.trim()).filter(Boolean);
      const { data } = await api.post('/forum/posts', { title: form.title, body: form.body, category: form.category, tags });
      toast.success('Posted!');
      setShowNew(false);
      setForm({ title: '', body: '', category: '', tags: '' });
      navigate(`/community-forum/${data.post_id}`);
    } catch (err) {
      toast.error(extractError(err, 'Failed to post'));
    } finally {
      setCreating(false);
    }
  };

  const activeCategoryMeta = useMemo(() => categories.find((c) => c.id === activeCat), [categories, activeCat]);

  const audienceName = audience === 'provider' ? 'Trade Pros Community' : 'Homeowner Community';
  const audienceSub = audience === 'provider' ? 'Real talk from NZ tradies about pricing, projects and the business' : 'Ask, share, review — from renovation journeys to weekend fixes';

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-6">
      {/* Header banner */}
      <div className="relative overflow-hidden rounded-3xl mb-6 bg-gradient-to-br from-primary via-blue-700 to-indigo-800 p-6 md:p-8 text-white">
        <div className="absolute -right-10 -top-10 w-64 h-64 rounded-full bg-white/10 blur-3xl" />
        <div className="absolute -left-16 -bottom-20 w-72 h-72 rounded-full bg-white/5 blur-3xl" />
        <div className="relative flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/20 backdrop-blur text-xs font-semibold uppercase tracking-wider">
              <Users className="w-3.5 h-3.5" />
              {audienceName}
            </div>
            <h1 className="mt-3 text-2xl md:text-3xl font-bold tracking-tight">Property maintenance & renovations, together.</h1>
            <p className="mt-1 text-sm md:text-base text-white/80 max-w-2xl">{audienceSub}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button data-testid="forum-new-post-btn" onClick={() => setShowNew(true)} size="lg" className="bg-white text-primary hover:bg-white/90 shadow-lg">
              <Plus className="w-4 h-4 mr-1.5" /> New Post
            </Button>
          </div>
        </div>
        {stats && (
          <div className="relative mt-6 grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Posts', v: stats.posts },
              { label: 'Replies', v: stats.replies },
              { label: 'Members', v: stats.members },
              { label: 'Active 24h', v: stats.active_today },
            ].map((s) => (
              <div key={s.label} className="bg-white/10 backdrop-blur rounded-xl p-3">
                <div className="text-2xl font-bold tabular-nums">{s.v}</div>
                <div className="text-xs text-white/70">{s.label}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr_260px] gap-6">
        {/* LEFT: Categories */}
        <aside className="hidden lg:block">
          <div className="sticky top-4 space-y-1">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-2 mb-1.5">Communities</div>
            <button
              data-testid="forum-cat-all"
              onClick={() => setActiveCat('all')}
              className={`w-full flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm transition-colors ${activeCat === 'all' ? 'bg-primary/10 text-primary font-semibold' : 'hover:bg-accent text-muted-foreground hover:text-foreground'}`}
            >
              <div className="w-7 h-7 rounded-md bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center text-white"><Sparkles className="w-3.5 h-3.5" /></div>
              <span className="truncate">All communities</span>
            </button>
            {categories.map((c) => (
              <button
                key={c.id}
                data-testid={`forum-cat-${c.id}`}
                onClick={() => setActiveCat(c.id)}
                className={`w-full flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm transition-colors ${activeCat === c.id ? 'bg-primary/10 text-primary font-semibold' : 'hover:bg-accent text-muted-foreground hover:text-foreground'}`}
              >
                <CategoryIcon icon={c.icon} color={c.color} className="w-3.5 h-3.5" />
                <span className="truncate flex-1 text-left">{c.name}</span>
              </button>
            ))}
          </div>
        </aside>

        {/* CENTER: Post feed */}
        <div>
          {/* Filter bar */}
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <div className="inline-flex bg-muted rounded-lg p-0.5" role="tablist">
              {SORT_TABS.map((t) => {
                const Icon = t.icon;
                return (
                  <button
                    key={t.id}
                    data-testid={`forum-sort-${t.id}`}
                    onClick={() => setSort(t.id)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${sort === t.id ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {t.label}
                  </button>
                );
              })}
            </div>
            <div className="relative flex-1 min-w-[200px]">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                data-testid="forum-search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') loadPosts(); }}
                placeholder="Search posts, tags, projects..."
                className="pl-9"
              />
            </div>
            {/* Mobile cat select */}
            <div className="lg:hidden w-full">
              <Select value={activeCat} onValueChange={setActiveCat}>
                <SelectTrigger><SelectValue placeholder="Category" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All communities</SelectItem>
                  {categories.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>

          {activeCategoryMeta && (
            <div className="flex items-center gap-3 p-4 rounded-2xl border border-border bg-card mb-4">
              <CategoryIcon icon={activeCategoryMeta.icon} color={activeCategoryMeta.color} />
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-foreground">{activeCategoryMeta.name}</div>
                <div className="text-xs text-muted-foreground">{activeCategoryMeta.desc}</div>
              </div>
              <button onClick={() => setActiveCat('all')} className="text-xs text-muted-foreground hover:text-foreground p-1 rounded-md hover:bg-accent"><X className="w-4 h-4" /></button>
            </div>
          )}

          {/* Post list */}
          {loading ? (
            <div className="flex items-center justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
          ) : posts.length === 0 ? (
            <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
              <MessageCircle className="w-10 h-10 mx-auto text-muted-foreground mb-3 opacity-40" />
              <div className="font-medium text-foreground">Nothing here yet</div>
              <p className="text-sm text-muted-foreground mt-1">Be the first to start a conversation.</p>
              <Button className="mt-4" onClick={() => setShowNew(true)}><Plus className="w-4 h-4 mr-1" /> Create post</Button>
            </div>
          ) : (
            <div className="space-y-3">
              {posts.map((p) => {
                const cat = categories.find((c) => c.id === p.category);
                const badge = roleBadge(p.author_role);
                return (
                  <div
                    key={p.post_id}
                    data-testid={`forum-post-${p.post_id}`}
                    onClick={() => navigate(`/community-forum/${p.post_id}`)}
                    className="group bg-card border border-border rounded-2xl p-4 hover:border-primary/40 hover:shadow-md hover:shadow-primary/5 transition-all cursor-pointer"
                  >
                    <div className="flex gap-4">
                      <VoteControl testId={`forum-post-${p.post_id}`} score={p.score} userVote={p.user_vote} onVote={(v) => handleVote(p.post_id, v)} />
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground mb-1.5">
                          {cat && (
                            <span className="inline-flex items-center gap-1.5 font-semibold" style={{ color: cat.color }}>
                              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: cat.color }} />
                              {cat.name}
                            </span>
                          )}
                          <span>·</span>
                          <span>by <span className="text-foreground font-medium">{p.author_name}</span></span>
                          <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold ${badge.cls}`}>{badge.label}</span>
                          <span>·</span>
                          <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" /> {timeAgo(p.created_at)}</span>
                          {p.pinned && <span className="inline-flex items-center gap-1 text-primary font-semibold"><Pin className="w-3 h-3" /> Pinned</span>}
                        </div>
                        <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors leading-snug">{p.title}</h3>
                        <p className="mt-1 text-sm text-muted-foreground line-clamp-2">{p.body}</p>
                        {p.tags?.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {p.tags.map((t) => (
                              <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-muted text-[10px] font-medium text-muted-foreground">
                                <TagIcon className="w-2.5 h-2.5" /> {t}
                              </span>
                            ))}
                          </div>
                        )}
                        <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                          <span className="inline-flex items-center gap-1"><MessageCircle className="w-3.5 h-3.5" /> {p.replies_count} {p.replies_count === 1 ? 'reply' : 'replies'}</span>
                          <span className="inline-flex items-center gap-1"><Eye className="w-3.5 h-3.5" /> {p.views}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* RIGHT: Sidebar */}
        <aside className="hidden lg:block">
          <div className="sticky top-4 space-y-4">
            <div className="bg-card border border-border rounded-2xl p-4">
              <div className="flex items-center gap-2 font-semibold text-foreground"><ShieldCheck className="w-4 h-4 text-emerald-500" /> Community Guidelines</div>
              <ul className="mt-3 text-xs text-muted-foreground space-y-1.5 list-disc pl-4">
                <li>Be respectful — trade insults get you banned.</li>
                <li>No self-promo without value. Share cost breakdowns freely.</li>
                <li>Verify claims: quote real numbers, tag photos.</li>
                <li>Warranty disputes belong in Disputes, not here.</li>
              </ul>
            </div>
            <div className="bg-gradient-to-br from-primary/10 via-blue-500/5 to-transparent border border-primary/20 rounded-2xl p-4">
              <div className="font-semibold text-foreground">Got a project?</div>
              <p className="mt-1 text-xs text-muted-foreground">Post your journey — before/after threads get the most engagement in the community.</p>
              <Button size="sm" onClick={() => setShowNew(true)} className="mt-3 w-full">Start a thread</Button>
            </div>
            <div className="bg-card border border-border rounded-2xl p-4">
              <div className="text-xs font-semibold uppercase text-muted-foreground tracking-wider mb-2">Top tags this week</div>
              <div className="flex flex-wrap gap-1.5">
                {['bathroom', 'healthy-homes', 'heat-pump', 'renovation', 'quotes', 'insulation', 'tiling', 'roof'].map((t) => (
                  <span key={t} className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-muted text-[11px] font-medium text-muted-foreground hover:bg-primary/10 hover:text-primary cursor-pointer transition-colors" onClick={() => { setQ(t); }}>
                    <TagIcon className="w-2.5 h-2.5" /> {t}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </aside>
      </div>

      {/* NEW POST DIALOG */}
      <Dialog open={showNew} onOpenChange={setShowNew}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle className="flex items-center gap-2"><Plus className="w-4 h-4" /> Create post</DialogTitle></DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4 mt-2">
            <div>
              <Label>Community</Label>
              <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                <SelectTrigger data-testid="new-post-category" className="mt-1.5"><SelectValue placeholder="Pick a community" /></SelectTrigger>
                <SelectContent>
                  {categories.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Title</Label>
              <Input
                data-testid="new-post-title"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="e.g. Full bathroom reno — $22k breakdown"
                className="mt-1.5"
                required
                minLength={5}
              />
            </div>
            <div>
              <Label>Details</Label>
              <Textarea
                data-testid="new-post-body"
                value={form.body}
                onChange={(e) => setForm({ ...form, body: e.target.value })}
                placeholder="Share numbers, timelines, photos in words — real detail = real replies."
                rows={7}
                className="mt-1.5"
                required
                minLength={10}
              />
            </div>
            <div>
              <Label>Tags (comma-separated, max 5)</Label>
              <Input
                data-testid="new-post-tags"
                value={form.tags}
                onChange={(e) => setForm({ ...form, tags: e.target.value })}
                placeholder="bathroom, renovation, quotes"
                className="mt-1.5"
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowNew(false)}>Cancel</Button>
              <Button data-testid="new-post-submit" type="submit" disabled={creating}>
                {creating ? <><Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> Posting...</> : <><Send className="w-4 h-4 mr-1.5" /> Post</>}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
