import React, { useEffect, useState } from 'react';
import { Plus, Heart, MessageCircle, Share2, ShieldCheck, Bookmark } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import api from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';

const filters = [
  { k: 'all', l: 'All' },
  { k: 'article', l: 'Article' },
  { k: 'update', l: 'Update' },
  { k: 'report', l: 'Report' },
  { k: 'sale', l: 'Sale' },
  { k: 'news', l: 'News' },
];

const typeColors = {
  sale: 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300',
  news: 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300',
  article: 'bg-violet-100 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300',
  update: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300',
  report: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
};

export default function NewsFeed() {
  const [posts, setPosts] = useState([]);
  const [filter, setFilter] = useState('all');
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ title: '', content: '', post_type: 'news', tags: '' });

  const load = async () => {
    const r = await api.get('/feed', { params: filter !== 'all' ? { post_type: filter } : {} });
    setPosts(r.data);
  };
  useEffect(() => { load(); }, [filter]);

  const submit = async () => {
    if (!form.title || !form.content) return;
    await api.post('/feed', { ...form, tags: form.tags.split(',').map((t) => t.trim()).filter(Boolean) });
    toast.success('Posted!');
    setOpen(false);
    setForm({ title: '', content: '', post_type: 'news', tags: '' });
    load();
  };

  const toggleLike = async (post_id) => {
    await api.post(`/feed/${post_id}/like`);
    load();
  };

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-foreground">News Feed</h1>
        {user?.role === 'provider' && (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild><Button><Plus className="w-4 h-4 mr-1" /> Post</Button></DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>Create a post</DialogTitle></DialogHeader>
              <div className="space-y-3 mt-2">
                <div><Label>Title</Label><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="mt-1.5" /></div>
                <div><Label>Type</Label>
                  <Select value={form.post_type} onValueChange={(v) => setForm({ ...form, post_type: v })}>
                    <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="news">News</SelectItem>
                      <SelectItem value="sale">Sale</SelectItem>
                      <SelectItem value="article">Article</SelectItem>
                      <SelectItem value="update">Update</SelectItem>
                      <SelectItem value="report">Report</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div><Label>Content</Label><Textarea rows={5} value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} className="mt-1.5" /></div>
                <div><Label>Tags (comma separated)</Label><Input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder="plumbing, auckland" className="mt-1.5" /></div>
                <Button onClick={submit} className="w-full">Publish</Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="flex gap-2 mb-4 flex-wrap">
        {filters.map((f) => (
          <button key={f.k} onClick={() => setFilter(f.k)} className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${filter === f.k ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>{f.l}</button>
        ))}
      </div>

      <div className="space-y-4">
        {posts.map((p) => {
          const liked = p.liked_by?.includes(user?.user_id);
          return (
            <div key={p.post_id} className="bg-card border border-border rounded-2xl p-5">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-blue-600 text-white text-xs font-semibold flex items-center justify-center shrink-0">
                  {p.author_name.split(' ').map((s) => s[0]).slice(0, 2).join('')}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-semibold text-foreground">{p.author_name}</span>
                    {p.author_verified && <ShieldCheck className="w-3.5 h-3.5 text-primary" />}
                    <Badge className={typeColors[p.post_type] || ''}>{p.post_type}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">{p.author_category} · {formatDistanceToNow(new Date(p.created_at), { addSuffix: true })}</div>
                </div>
              </div>
              <h3 className="mt-3 font-semibold text-foreground">{p.title}</h3>
              <p className="mt-2 text-sm text-foreground/90 whitespace-pre-wrap">{p.content}</p>
              {p.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {p.tags.map((t) => <span key={t} className="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded-full">#{t}</span>)}
                </div>
              )}
              <div className="mt-4 pt-3 border-t border-border flex items-center gap-4">
                <button onClick={() => toggleLike(p.post_id)} className={`inline-flex items-center gap-1.5 text-sm ${liked ? 'text-rose-500' : 'text-muted-foreground hover:text-foreground'} transition-colors`}>
                  <Heart className={`w-4 h-4 ${liked ? 'fill-current' : ''}`} /> {p.likes || 0}
                </button>
                <button className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
                  <MessageCircle className="w-4 h-4" /> {p.comments_count || 0}
                </button>
                <button className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors ml-auto">
                  <Share2 className="w-4 h-4" />
                </button>
                <button className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
                  <Bookmark className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
