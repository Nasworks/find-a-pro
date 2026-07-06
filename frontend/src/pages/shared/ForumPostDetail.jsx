import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, ArrowUp, ArrowDown, MessageCircle, Eye, Clock, Trash2, Send, Loader2, Tag as TagIcon, Share2, Pin, X } from 'lucide-react';
import * as LucideIcons from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Textarea } from '../../components/ui/textarea';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';
import api from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import { extractError } from '../../lib/errors';

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

const roleBadgeMap = {
  provider: { label: 'Pro', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300' },
  customer: { label: 'Homeowner', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300' },
  landlord: { label: 'Landlord', cls: 'bg-orange-100 text-orange-700 dark:bg-orange-950/60 dark:text-orange-300' },
  property: { label: 'Property Mgr', cls: 'bg-violet-100 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300' },
  facilities: { label: 'Facilities', cls: 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-200' },
  insurance: { label: 'Insurance', cls: 'bg-teal-100 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300' },
};

function VoteBar({ score, userVote, onVote, vertical = false, testId }) {
  const wrapCls = vertical ? 'flex flex-col items-center gap-0.5' : 'inline-flex items-center gap-1';
  return (
    <div className={wrapCls}>
      <button
        data-testid={testId ? `${testId}-upvote` : undefined}
        onClick={() => onVote(userVote === 1 ? 0 : 1)}
        className={`w-7 h-7 rounded-md flex items-center justify-center transition-colors ${userVote === 1 ? 'text-orange-500 bg-orange-500/10' : 'text-muted-foreground hover:text-orange-500 hover:bg-orange-500/10'}`}
      >
        <ArrowUp className="w-4 h-4" />
      </button>
      <span className={`text-sm font-bold tabular-nums ${vertical ? '' : 'px-1'} ${userVote === 1 ? 'text-orange-500' : userVote === -1 ? 'text-blue-500' : 'text-foreground'}`}>{score}</span>
      <button
        data-testid={testId ? `${testId}-downvote` : undefined}
        onClick={() => onVote(userVote === -1 ? 0 : -1)}
        className={`w-7 h-7 rounded-md flex items-center justify-center transition-colors ${userVote === -1 ? 'text-blue-500 bg-blue-500/10' : 'text-muted-foreground hover:text-blue-500 hover:bg-blue-500/10'}`}
      >
        <ArrowDown className="w-4 h-4" />
      </button>
    </div>
  );
}

function CategoryIcon({ icon, color }) {
  const Icon = LucideIcons[icon] || LucideIcons.Hash;
  return (
    <div className="rounded-md flex items-center justify-center text-white shrink-0" style={{ backgroundColor: color, width: 28, height: 28 }}>
      <Icon className="w-3.5 h-3.5" />
    </div>
  );
}

function AuthorLine({ name, role, at }) {
  const badge = roleBadgeMap[role] || roleBadgeMap.customer;
  return (
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap">
      <div className="w-6 h-6 rounded-full bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center text-white text-[10px] font-bold">{(name || '?').slice(0, 1).toUpperCase()}</div>
      <span className="text-foreground font-medium">{name}</span>
      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold ${badge.cls}`}>{badge.label}</span>
      <span>·</span>
      <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" /> {timeAgo(at)}</span>
    </div>
  );
}

export default function ForumPostDetail() {
  const { postId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState(null);
  const [replyText, setReplyText] = useState('');
  const [replyTo, setReplyTo] = useState(null);
  const [posting, setPosting] = useState(false);

  const loadPost = useCallback(async () => {
    setLoading(true);
    try {
      const [d, c] = await Promise.all([
        api.get(`/forum/posts/${postId}`),
        api.get('/forum/categories'),
      ]);
      setData(d.data);
      setCategory(c.data.categories.find((cat) => cat.id === d.data.post.category));
    } catch (err) {
      toast.error(extractError(err, 'Failed to load post'));
      navigate('/community-forum');
    } finally {
      setLoading(false);
    }
  }, [postId, navigate]);

  useEffect(() => { loadPost(); }, [loadPost]);

  const votePost = async (value) => {
    setData((prev) => {
      if (!prev) return prev;
      const prev_v = prev.post.user_vote || 0;
      return { ...prev, post: { ...prev.post, user_vote: value, score: (prev.post.score || 0) + (value - prev_v) } };
    });
    try { await api.post(`/forum/posts/${postId}/vote`, { value }); }
    catch (err) { toast.error(extractError(err, 'Vote failed')); loadPost(); }
  };

  const voteReply = async (replyId, value) => {
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        replies: prev.replies.map((r) => {
          if (r.reply_id !== replyId) return r;
          const prev_v = r.user_vote || 0;
          return { ...r, user_vote: value, score: (r.score || 0) + (value - prev_v) };
        }),
      };
    });
    try { await api.post(`/forum/replies/${replyId}/vote`, { value }); }
    catch (err) { toast.error(extractError(err, 'Vote failed')); loadPost(); }
  };

  const submitReply = async (e) => {
    e.preventDefault();
    if (replyText.trim().length < 2) return toast.error('Say a bit more');
    setPosting(true);
    try {
      await api.post(`/forum/posts/${postId}/replies`, { body: replyText.trim(), parent_reply_id: replyTo });
      setReplyText('');
      setReplyTo(null);
      await loadPost();
      toast.success('Reply posted');
    } catch (err) {
      toast.error(extractError(err, 'Failed to reply'));
    } finally {
      setPosting(false);
    }
  };

  const deletePost = async () => {
    if (!window.confirm('Delete this post permanently?')) return;
    try {
      await api.delete(`/forum/posts/${postId}`);
      toast.success('Deleted');
      navigate('/community-forum');
    } catch (err) { toast.error(extractError(err, 'Delete failed')); }
  };

  const sharePost = () => {
    const url = window.location.href;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url);
      toast.success('Link copied to clipboard');
    }
  };

  const handleReplyTo = (replyId, authorName) => {
    setReplyTo(replyId);
    setReplyText((prev) => (prev ? prev : `@${authorName} `));
    // Scroll composer into view
    setTimeout(() => {
      const el = document.querySelector('[data-testid="forum-composer"]');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      const input = document.querySelector('[data-testid="forum-reply-input"]');
      if (input) input.focus();
    }, 100);
  };

  if (loading || !data) {
    return <div className="flex items-center justify-center py-24"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>;
  }

  const { post, replies } = data;
  const isOwner = user?.user_id === post.author_id;

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-6" data-testid="forum-post-detail">
      <button onClick={() => navigate('/community-forum')} data-testid="forum-back" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to community
      </button>

      {/* POST */}
      <article className="bg-card border border-border rounded-2xl p-5 md:p-6">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {category && (
            <Link to="/community-forum" className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full border border-border hover:border-primary/40 transition-colors">
              <CategoryIcon icon={category.icon} color={category.color} />
              <span className="text-xs font-semibold text-foreground">{category.name}</span>
            </Link>
          )}
          {post.pinned && (
            <Badge className="bg-primary/10 text-primary border-primary/20"><Pin className="w-3 h-3 mr-1" /> Pinned</Badge>
          )}
          <div className="ml-auto flex items-center gap-1">
            <Button size="sm" variant="outline" onClick={sharePost}><Share2 className="w-3.5 h-3.5 mr-1" /> Share</Button>
            {isOwner && (
              <Button size="sm" variant="outline" onClick={deletePost} data-testid="forum-delete-post" className="text-rose-500 hover:text-rose-600"><Trash2 className="w-3.5 h-3.5" /></Button>
            )}
          </div>
        </div>

        <h1 className="text-2xl md:text-3xl font-bold text-foreground leading-tight" data-testid="forum-post-title">{post.title}</h1>
        <div className="mt-3">
          <AuthorLine name={post.author_name} role={post.author_role} at={post.created_at} />
        </div>

        <div className="mt-4 text-foreground whitespace-pre-wrap leading-relaxed" data-testid="forum-post-body">{post.body}</div>

        {post.tags?.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {post.tags.map((t) => (
              <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-muted text-xs font-medium text-muted-foreground">
                <TagIcon className="w-3 h-3" /> {t}
              </span>
            ))}
          </div>
        )}

        <div className="mt-5 pt-4 border-t border-border flex items-center gap-4">
          <VoteBar testId="forum-post" score={post.score} userVote={post.user_vote} onVote={votePost} />
          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><MessageCircle className="w-3.5 h-3.5" /> {post.replies_count} replies</span>
          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Eye className="w-3.5 h-3.5" /> {post.views} views</span>
        </div>
      </article>

      {/* REPLY COMPOSER */}
      <form onSubmit={submitReply} className="mt-6 bg-card border border-border rounded-2xl p-4" data-testid="forum-composer">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-semibold text-foreground">{replyTo ? 'Replying to a comment' : 'Add your reply'}</div>
          {replyTo && (
            <button type="button" onClick={() => setReplyTo(null)} className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1"><X className="w-3 h-3" /> Cancel thread</button>
          )}
        </div>
        <Textarea
          data-testid="forum-reply-input"
          value={replyText}
          onChange={(e) => setReplyText(e.target.value)}
          placeholder={replyTo ? "Reply to that comment..." : "Share your experience, ask a follow-up, or offer advice..."}
          rows={3}
          required
        />
        <div className="mt-2 flex items-center justify-between">
          <div className="text-xs text-muted-foreground">Posting as <span className="text-foreground font-medium">{user?.name}</span></div>
          <Button data-testid="forum-reply-submit" type="submit" disabled={posting || replyText.trim().length < 2}>
            {posting ? <><Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> Sending...</> : <><Send className="w-4 h-4 mr-1.5" /> Reply</>}
          </Button>
        </div>
      </form>

      {/* REPLIES — threaded */}
      <div className="mt-6">
        <div className="text-sm font-semibold text-foreground mb-3">{replies.length} {replies.length === 1 ? 'reply' : 'replies'}</div>
        {replies.length === 0 ? (
          <div className="bg-card border border-dashed border-border rounded-2xl p-8 text-center">
            <MessageCircle className="w-8 h-8 mx-auto text-muted-foreground mb-2 opacity-40" />
            <p className="text-sm text-muted-foreground">Be the first to reply</p>
          </div>
        ) : (
          <ReplyTree replies={replies} onVote={voteReply} onReplyTo={handleReplyTo} />
        )}
      </div>
    </div>
  );
}

// Flatten the reply tree into a rendering list with depth info.
function flattenTree(replies) {
  const byId = new Map();
  replies.forEach((r) => byId.set(r.reply_id, { ...r, children: [] }));
  const roots = [];
  byId.forEach((node) => {
    const parentId = node.parent_reply_id;
    if (parentId && byId.has(parentId)) byId.get(parentId).children.push(node);
    else roots.push(node);
  });
  const flat = [];
  const walk = (nodes, depth) => {
    nodes.forEach((n) => {
      flat.push({ node: n, depth });
      if (n.children.length) walk(n.children, Math.min(depth + 1, 4));
    });
  };
  walk(roots, 0);
  return flat;
}

function ReplyTree({ replies, onVote, onReplyTo }) {
  const flat = flattenTree(replies);
  return (
    <div className="space-y-3">
      {flat.map(({ node, depth }) => (
        <ReplyItem key={node.reply_id} node={node} depth={depth} onVote={onVote} onReplyTo={onReplyTo} />
      ))}
    </div>
  );
}

function ReplyItem({ node, depth, onVote, onReplyTo }) {
  const indent = depth > 0 ? { marginLeft: depth * 16 } : undefined;
  return (
    <div style={indent} className={depth > 0 ? 'relative pl-4 border-l-2 border-border' : ''}>
      <div className="bg-card border border-border rounded-2xl p-4 flex gap-3" data-testid={`forum-reply-${node.reply_id}`}>
        <VoteBar
          vertical
          testId={`forum-reply-${node.reply_id}`}
          score={node.score}
          userVote={node.user_vote}
          onVote={(v) => onVote(node.reply_id, v)}
        />
        <div className="flex-1 min-w-0">
          <AuthorLine name={node.author_name} role={node.author_role} at={node.created_at} />
          <div className="mt-2 text-sm text-foreground whitespace-pre-wrap leading-relaxed">{node.body}</div>
          <div className="mt-2">
            <button
              onClick={() => onReplyTo(node.reply_id, node.author_name)}
              data-testid={`forum-reply-reply-${node.reply_id}`}
              className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-primary transition-colors"
            >
              <MessageCircle className="w-3 h-3" /> Reply
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
