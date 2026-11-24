import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, MapPin, Clock, DollarSign, ShieldCheck, Star, Paperclip, Send, MessageSquare, FileText, Users, Award, Plus, Minus, X, Check, RotateCcw, Info, TrendingUp, Upload, Trash2 } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Checkbox } from '../../components/ui/checkbox';
import api from '../../lib/api';
import { JobInvoice } from '../../components/JobInvoice';
import JobMatchesPanel from '../../components/JobMatchesPanel';
import ProjectTimeline from '../../components/ProjectTimeline';
import { SIZE_META, priceLine } from '../../components/MatchedJobsFeed';
import { MediaThumb, mediaSrc, isVideo } from '../../components/MediaUploader';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';

export default function JobDetail() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [tab, setTab] = useState('overview');
  const [openBid, setOpenBid] = useState(null); // { mode: 'new' | 'counter', bid?: bid }
  const [selectedBidId, setSelectedBidId] = useState(null);

  const load = async () => {
    try {
      const r = await api.get(`/jobs/${jobId}`);
      setData(r.data);
    } catch {
      toast.error('Job not found');
      navigate(-1);
    }
  };
  useEffect(() => { load(); }, [jobId]);

  if (!data) return <div className="p-10 text-center text-muted-foreground">Loading...</div>;
  const { job, bids } = data;
  const isOwner = user?.user_id === job.client_id;
  const isOpenJob = ['open', 'matched'].includes(job.status);
  const canSeeMatches = isOwner || user?.user_id === job.approver_id;
  const myBid = bids.find((b) => b.provider_id === user?.user_id && b.status === 'pending');
  // Show only latest revision per provider chain
  const activeBids = bids.filter((b) => !bids.some((x) => x.previous_bid_id === b.bid_id));
  const amounts = activeBids.filter((b) => b.status !== 'withdrawn' && b.status !== 'rejected').map((b) => b.amount);
  const bidStats = amounts.length ? { min: Math.min(...amounts), max: Math.max(...amounts), avg: amounts.reduce((s, a) => s + a, 0) / amounts.length, count: amounts.length } : null;

  const selectedBid = selectedBidId ? bids.find((b) => b.bid_id === selectedBidId) : null;

  // Memoized sort of active bids by amount (ascending, lowest first)
  const sortedActiveBids = [...activeBids].sort((a, b) => a.amount - b.amount);

  const acceptBid = async (bid_id) => {
    await api.post(`/bids/${bid_id}/accept`);
    toast.success('Bid accepted — booking created');
    load();
  };
  const rejectBid = async (bid_id) => {
    await api.post(`/bids/${bid_id}/reject`);
    toast.success('Bid rejected');
    load();
  };
  const withdrawBid = async (bid_id) => {
    await api.post(`/bids/${bid_id}/withdraw`);
    toast.success('Bid withdrawn');
    load();
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      {/* Job header */}
      <div className="bg-card border border-border rounded-2xl p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 capitalize">{job.status === 'done' ? 'completed' : job.status.replace('_', ' ')}{job.status === 'done' ? (job.payment_status === 'paid' ? ' · paid' : ' · unpaid') : ''}</Badge>
              <span className="text-xs text-muted-foreground">Posted {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}</span>
            </div>
            <h1 className="text-2xl font-bold text-foreground mt-2">{job.title}</h1>
            <div className="flex flex-wrap items-center gap-3 mt-3 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1"><MapPin className="w-3.5 h-3.5" /> {job.location}</span>
              <span className="inline-flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> {job.urgency}</span>
              <span className="capitalize">· {job.category}</span>
              {job.pricing_type && <Badge className={`${(SIZE_META[job.pricing_type] || SIZE_META.large_quote).cls} border-0`} data-testid="job-size-badge">{(SIZE_META[job.pricing_type] || SIZE_META.large_quote).l}</Badge>}
              <span className="inline-flex items-center gap-1"><DollarSign className="w-3.5 h-3.5" /> {priceLine(job)}</span>
              {job.preferred_date && <span className="inline-flex items-center gap-1" data-testid="job-preferred-date"><Clock className="w-3.5 h-3.5" /> Preferred {job.preferred_date}</span>}
            </div>
          </div>
          {bidStats && (
            <div className="bg-muted/40 rounded-xl p-3 text-right shrink-0">
              <div className="text-xs text-muted-foreground">{bidStats.count} active bids</div>
              <div className="text-lg font-bold text-foreground">${Math.round(bidStats.min)}–${Math.round(bidStats.max)}</div>
              <div className="text-xs text-muted-foreground">Avg ${Math.round(bidStats.avg)}</div>
            </div>
          )}
        </div>
        <p className="mt-4 text-foreground/90 whitespace-pre-wrap">{job.description}</p>
      </div>

      {(canSeeMatches || user?.user_id === job.assigned_provider_id) && ['assigned', 'in_progress', 'done'].includes(job.status) && job.assigned_provider_id && (
        <div className="mt-6 bg-card border border-border rounded-2xl p-5" data-testid="job-progress-section">
          <div className="font-semibold text-foreground mb-3">Project progress</div>
          <ProjectTimeline jobId={job.job_id} onChanged={load} />
        </div>
      )}

      {canSeeMatches && job.approval_status !== 'pending' && (
        <div className="mt-6"><JobMatchesPanel job={job} onAwarded={load} /></div>
      )}

      {/* Tabs */}
      <div className="mt-6 border-b border-border">
        <div className="flex gap-1 -mb-px overflow-x-auto">
          {[
            { k: 'overview', l: 'Overview' },
            { k: 'bids', l: `Bids (${activeBids.length})` },
            { k: 'documents', l: 'Documents' },
            { k: 'terms', l: 'Terms' },
          ].map((t) => (
            <button key={t.k} onClick={() => setTab(t.k)} className={`px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${tab === t.k ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>{t.l}</button>
          ))}
        </div>
      </div>

      {/* Content */}
      {tab === 'overview' && (
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
          <div className="space-y-4">
            <div className="bg-card border border-border rounded-2xl p-5">
              <h3 className="font-semibold text-foreground mb-3">Job details</h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-muted-foreground">Category</span><div className="font-medium capitalize">{job.category}</div></div>
                <div><span className="text-muted-foreground">Urgency</span><div className="font-medium capitalize">{job.urgency.replace('_', ' ')}</div></div>
                <div><span className="text-muted-foreground">Location</span><div className="font-medium">{job.location}</div></div>
                <div><span className="text-muted-foreground">Budget</span><div className="font-medium">{priceLine(job)}</div></div>
                <div><span className="text-muted-foreground">Job size</span><div className="font-medium">{(SIZE_META[job.pricing_type] || SIZE_META.large_quote).l}</div></div>
                <div><span className="text-muted-foreground">Bids received</span><div className="font-medium">{activeBids.length}</div></div>
              </div>
            </div>
            {bidStats && (
              <div className="bg-card border border-border rounded-2xl p-5">
                <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2"><TrendingUp className="w-4 h-4 text-primary" /> Bid statistics</h3>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div><div className="text-xs text-muted-foreground">Lowest</div><div className="text-xl font-bold text-foreground">${Math.round(bidStats.min)}</div></div>
                  <div><div className="text-xs text-muted-foreground">Average</div><div className="text-xl font-bold text-primary">${Math.round(bidStats.avg)}</div></div>
                  <div><div className="text-xs text-muted-foreground">Highest</div><div className="text-xl font-bold text-foreground">${Math.round(bidStats.max)}</div></div>
                </div>
                <div className="mt-4 h-2 rounded-full bg-muted overflow-hidden relative">
                  <div className="absolute h-full bg-gradient-to-r from-emerald-500 via-primary to-rose-500" style={{ left: 0, right: 0 }} />
                </div>
              </div>
            )}
            {job.photos?.length > 0 && (
              <div className="bg-card border border-border rounded-2xl p-5" data-testid="job-overview-media">
                <h3 className="font-semibold text-foreground mb-3">Photos & videos</h3>
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                  {job.photos.slice(0, 8).map((p) => (
                    <button key={p} type="button" onClick={() => setTab('documents')} className="aspect-square rounded-lg overflow-hidden bg-muted"><MediaThumb url={p} /></button>
                  ))}
                </div>
              </div>
            )}
            {job.status !== 'open' && <JobInvoice jobId={job.job_id} hideWhenEmpty />}
          </div>
          <aside className="space-y-4">
            {!isOwner && user?.role === 'provider' && isOpenJob && !myBid && (
              <Button className="w-full" size="lg" onClick={() => setOpenBid({ mode: 'new' })}>Submit a Bid</Button>
            )}
            {isOwner && isOpenJob && activeBids.length > 0 && (
              <Button className="w-full" size="lg" onClick={() => setTab('bids')}>Review {activeBids.length} bids</Button>
            )}
            <div className="bg-card border border-border rounded-2xl p-4 text-sm">
              <div className="flex items-center gap-2 font-semibold text-foreground"><ShieldCheck className="w-4 h-4 text-emerald-500" /> Pro Finder Protection</div>
              <p className="text-xs text-muted-foreground mt-2">Every provider is background-checked, insured, and rated. Payments held in escrow until work is verified.</p>
            </div>
          </aside>
        </div>
      )}

      {tab === 'bids' && (
        <div className="mt-6 space-y-4">
          {/* Provider actions */}
          {!isOwner && user?.role === 'provider' && isOpenJob && !myBid && (
            <div className="bg-primary/5 border border-primary/20 rounded-2xl p-4 flex items-center justify-between">
              <div>
                <div className="font-semibold text-foreground">Ready to bid?</div>
                <div className="text-sm text-muted-foreground">Submit a detailed proposal with breakdown, timeline & terms.</div>
              </div>
              <Button onClick={() => setOpenBid({ mode: 'new' })}><Plus className="w-4 h-4 mr-1" /> Submit Bid</Button>
            </div>
          )}
          {myBid && !isOwner && (
            <div className="bg-emerald-50 border border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-800 rounded-2xl p-4 flex items-center justify-between">
              <div>
                <div className="font-semibold text-emerald-800 dark:text-emerald-200">Your bid is active</div>
                <div className="text-sm text-emerald-700 dark:text-emerald-300">You bid ${myBid.amount} · Revision {myBid.revision}</div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => setOpenBid({ mode: 'counter', bid: myBid })}><RotateCcw className="w-3.5 h-3.5 mr-1" /> Revise</Button>
                <Button size="sm" variant="outline" onClick={() => withdrawBid(myBid.bid_id)}>Withdraw</Button>
              </div>
            </div>
          )}

          {/* Bids list */}
          {activeBids.length === 0 ? (
            <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
              <MessageSquare className="w-8 h-8 mx-auto text-muted-foreground mb-2 opacity-40" />
              <div className="font-medium text-foreground">No bids yet</div>
              <div className="text-sm text-muted-foreground">Providers will start submitting bids soon.</div>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
              <div className="space-y-3">
                {sortedActiveBids.map((b) => (
                  <BidCard key={b.bid_id} bid={b} bids={bids} selected={selectedBidId === b.bid_id} onSelect={() => setSelectedBidId(b.bid_id)} isOwner={isOwner} onAccept={() => acceptBid(b.bid_id)} onReject={() => rejectBid(b.bid_id)} onCounter={() => setOpenBid({ mode: 'counter', bid: b })} isMe={b.provider_id === user?.user_id} />
                ))}
              </div>
              <div className="lg:sticky lg:top-24 lg:self-start">
                {selectedBid ? (
                  <BidCommentPanel bid={selectedBid} isOwner={isOwner} onRefresh={load} />
                ) : (
                  <div className="bg-card border border-dashed border-border rounded-2xl p-6 text-center text-sm text-muted-foreground">
                    Select a bid to open the discussion thread
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'documents' && (
        <div className="mt-6 bg-card border border-border rounded-2xl p-6">
          <h3 className="font-semibold text-foreground mb-3">Photos, videos & documents</h3>
          {job.photos?.length ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3" data-testid="job-media-gallery">
              {job.photos.map((p) => (isVideo(p)
                ? <video key={p} src={mediaSrc(p)} controls playsInline className="w-full h-32 object-cover rounded-lg bg-black" />
                : <a key={p} href={mediaSrc(p)} target="_blank" rel="noreferrer"><img src={mediaSrc(p)} className="w-full h-32 object-cover rounded-lg" alt="" /></a>))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No documents attached to this job yet. Providers may attach quotes, plans, or product spec sheets in their bids.</p>
          )}
        </div>
      )}

      {tab === 'terms' && (
        <div className="mt-6 bg-card border border-border rounded-2xl p-6 text-sm space-y-3 text-foreground/90">
          <h3 className="font-semibold text-foreground text-base">Standard Pro Finder NZ Terms</h3>
          <p><strong>1. Payment:</strong> Funds are held in escrow when a bid is accepted. Provider is paid on completion sign-off or after a 48h auto-release if no dispute is raised.</p>
          <p><strong>2. Warranty:</strong> All jobs include a standard 12-month workmanship warranty unless the provider offers longer terms in their bid.</p>
          <p><strong>3. Cancellation:</strong> Free cancellation up to 24 hours before scheduled start. Later cancellations may incur a 20% call-out fee.</p>
          <p><strong>4. Disputes:</strong> Pro Finder NZ mediates any dispute within 5 business days. Both parties may upload evidence.</p>
          <p><strong>5. Health & Safety:</strong> Providers must comply with NZ H&S at Work Act 2015. Insurance certificates available on request.</p>
          <p><strong>6. Additional terms:</strong> Each provider may include their own supplementary terms in their bid. Review carefully before accepting.</p>
        </div>
      )}

      {openBid && (
        <BidSubmissionDialog mode={openBid.mode} bid={openBid.bid} job={job} onClose={() => setOpenBid(null)} onSuccess={() => { setOpenBid(null); load(); }} />
      )}
    </div>
  );
}

function BidCard({ bid, bids, selected, onSelect, isOwner, onAccept, onReject, onCounter, isMe }) {
  const [expanded, setExpanded] = useState(false);
  // Count of revisions
  const revisions = bids.filter((b) => b.provider_id === bid.provider_id).length;
  const statusColors = {
    pending: 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300',
    accepted: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300',
    rejected: 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300',
    withdrawn: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    countered: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
  };
  return (
    <div className={`bg-card border rounded-2xl overflow-hidden transition-all ${selected ? 'border-primary shadow-sm shadow-primary/10' : 'border-border hover:border-primary/40'}`}>
      <div onClick={onSelect} className="p-4 cursor-pointer">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary to-blue-600 text-white text-xs font-bold flex items-center justify-center shrink-0">
              {bid.provider_name.split(' ').map((s) => s[0]).slice(0, 2).join('')}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="font-semibold text-foreground">{bid.provider_name}</span>
                {bid.provider_verified && <ShieldCheck className="w-3.5 h-3.5 text-primary" />}
                {isMe && <Badge variant="secondary" className="text-[10px]">Your bid</Badge>}
                <Badge className={statusColors[bid.status] || ''}>{bid.status}</Badge>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                <span className="inline-flex items-center gap-0.5"><Star className="w-3 h-3 fill-amber-400 text-amber-400" />{bid.provider_rating}</span>
                <span>({bid.provider_reviews || 0} reviews)</span>
                {revisions > 1 && <span>· Revision {bid.revision}</span>}
              </div>
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className="text-2xl font-bold text-primary">${bid.amount.toLocaleString()}</div>
            <div className="text-xs text-muted-foreground">ETA {bid.eta_days} days</div>
          </div>
        </div>
        <p className="text-sm text-foreground/80 mt-3 line-clamp-2">{bid.message}</p>

        {bid.line_items?.length > 0 && (
          <button onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }} className="mt-2 text-xs text-primary hover:underline inline-flex items-center gap-1">
            {expanded ? 'Hide' : 'Show'} price breakdown ({bid.line_items.length} items)
          </button>
        )}
        {expanded && bid.line_items?.length > 0 && (
          <div className="mt-2 border border-border rounded-lg overflow-hidden text-sm">
            <div className="grid grid-cols-[1fr_60px_100px_100px] gap-2 px-3 py-2 bg-muted/40 text-xs font-medium text-muted-foreground">
              <div>Item</div><div className="text-right">Qty</div><div className="text-right">Unit</div><div className="text-right">Total</div>
            </div>
            {bid.line_items.map((li, i) => (
              <div key={`${bid.bid_id}-li-${i}-${li.label}`} className="grid grid-cols-[1fr_60px_100px_100px] gap-2 px-3 py-2 border-t border-border">
                <div className="truncate">{li.label}</div>
                <div className="text-right">{li.qty}</div>
                <div className="text-right">${li.unit_price}</div>
                <div className="text-right font-medium">${(li.qty * li.unit_price).toFixed(2)}</div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
          {bid.warranty_months > 0 && <span className="inline-flex items-center gap-1"><Award className="w-3 h-3" /> {bid.warranty_months}mo warranty</span>}
          {bid.payment_terms && <span className="inline-flex items-center gap-1"><DollarSign className="w-3 h-3" /> {bid.payment_terms}</span>}
          {bid.documents?.length > 0 && <span className="inline-flex items-center gap-1"><Paperclip className="w-3 h-3" /> {bid.documents.length} doc{bid.documents.length !== 1 && 's'}</span>}
          {bid.start_date && <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" /> Start: {bid.start_date}</span>}
        </div>
      </div>

      {isOwner && bid.status === 'pending' && (
        <div className="border-t border-border px-4 py-3 flex gap-2 flex-wrap">
          <Button size="sm" onClick={(e) => { e.stopPropagation(); onAccept(); }} className="flex-1"><Check className="w-3.5 h-3.5 mr-1" /> Accept</Button>
          <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); onCounter(); }} className="flex-1"><RotateCcw className="w-3.5 h-3.5 mr-1" /> Counter</Button>
          <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); onReject(); }} className="text-destructive hover:text-destructive"><X className="w-3.5 h-3.5" /></Button>
        </div>
      )}
    </div>
  );
}

function BidCommentPanel({ bid, isOwner, onRefresh }) {
  const [comments, setComments] = useState([]);
  const [text, setText] = useState('');
  const scrollRef = useRef(null);
  const { user } = useAuth();

  const load = async () => {
    const r = await api.get(`/bids/${bid.bid_id}/comments`);
    setComments(r.data);
    setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight }), 50);
  };
  useEffect(() => { load(); }, [bid.bid_id]);

  const send = async () => {
    if (!text.trim()) return;
    await api.post(`/bids/${bid.bid_id}/comments`, { content: text });
    setText('');
    load();
  };

  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden h-[480px] flex flex-col">
      <div className="px-4 py-3 border-b border-border">
        <div className="font-semibold text-sm text-foreground">Discussion — {bid.provider_name}</div>
        <div className="text-xs text-muted-foreground">${bid.amount} · Revision {bid.revision}</div>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-2 bg-muted/20">
        {comments.length === 0 && <div className="text-center text-xs text-muted-foreground py-8">No messages yet — ask questions or clarify terms.</div>}
        {comments.map((c) => {
          const mine = c.author_id === user?.user_id;
          return (
            <div key={c.comment_id} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] px-3 py-1.5 rounded-2xl text-xs ${mine ? 'bg-primary text-primary-foreground rounded-br-sm' : 'bg-card border border-border rounded-bl-sm'}`}>
                {!mine && <div className="font-medium text-[10px] mb-0.5">{c.author_name} <span className="text-muted-foreground capitalize">({c.author_role})</span></div>}
                <div>{c.content}</div>
                <div className={`text-[9px] mt-0.5 ${mine ? 'opacity-70' : 'text-muted-foreground'}`}>{formatDistanceToNow(new Date(c.created_at), { addSuffix: true })}</div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="border-t border-border p-2 flex gap-2">
        <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()} placeholder="Ask a question or clarify..." className="flex-1 px-3 py-1.5 rounded-full bg-muted/40 border border-transparent focus:border-primary/40 focus:bg-background outline-none text-xs transition-all" />
        <Button onClick={send} disabled={!text.trim()} size="icon" className="rounded-full h-8 w-8"><Send className="w-3.5 h-3.5" /></Button>
      </div>
    </div>
  );
}

function BidSubmissionDialog({ mode, bid, job, onClose, onSuccess }) {
  const isCounter = mode === 'counter';
  const [form, setForm] = useState({
    amount: bid?.amount || '',
    message: bid?.message || '',
    eta_days: bid?.eta_days || 3,
    start_date: bid?.start_date || '',
    line_items: bid?.line_items?.length ? bid.line_items.map((li, i) => ({ ...li, _key: `li_${i}` })) : [{ _key: 'li_0', label: 'Labour', qty: 1, unit_price: 0 }],
    terms: bid?.terms || '',
    warranty_months: bid?.warranty_months || 12,
    payment_terms: bid?.payment_terms || '50% upfront, 50% on completion',
    documents: bid?.documents || [],
    acceptTerms: false,
  });
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const updateItem = (i, k, v) => setForm((f) => ({ ...f, line_items: f.line_items.map((it, idx) => idx === i ? { ...it, [k]: k === 'label' ? v : Number(v) || 0 } : it) }));
  const addItem = () => setForm((f) => ({ ...f, line_items: [...f.line_items, { _key: `li_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`, label: '', qty: 1, unit_price: 0 }] }));
  const removeItem = (i) => setForm((f) => ({ ...f, line_items: f.line_items.filter((_, idx) => idx !== i) }));

  const subtotal = form.line_items.reduce((s, i) => s + (i.qty || 0) * (i.unit_price || 0), 0);

  const onFile = (e) => {
    const files = Array.from(e.target.files || []);
    files.forEach((f) => {
      const reader = new FileReader();
      reader.onload = () => {
        setForm((prev) => ({ ...prev, documents: [...prev.documents, { _key: `doc_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`, name: f.name, size: `${(f.size / 1024).toFixed(1)} KB`, type: f.type, url: reader.result }] }));
      };
      reader.readAsDataURL(f);
    });
  };
  const removeDoc = (i) => setForm((f) => ({ ...f, documents: f.documents.filter((_, idx) => idx !== i) }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.acceptTerms) { toast.error('Please accept the standard terms'); return; }
    if (!form.amount || !form.message) { toast.error('Amount and message required'); return; }
    setSaving(true);
    try {
      const payload = {
        job_id: job.job_id,
        amount: Number(form.amount),
        message: form.message,
        eta_days: Number(form.eta_days),
        start_date: form.start_date || null,
        line_items: form.line_items.filter((i) => i.label),
        terms: form.terms,
        warranty_months: Number(form.warranty_months),
        payment_terms: form.payment_terms,
        documents: form.documents.map(({ acceptTerms, ...d }) => d),
      };
      if (isCounter && bid) {
        await api.post(`/bids/${bid.bid_id}/counter`, payload);
      } else {
        await api.post('/bids', payload);
      }
      toast.success(isCounter ? 'Counter-offer submitted' : 'Bid submitted');
      onSuccess();
    } catch (err) {
      toast.error('Failed to submit');
    } finally { setSaving(false); }
  };

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto scrollbar-thin">
        <DialogHeader>
          <DialogTitle>{isCounter ? 'Revise / counter your bid' : 'Submit a bid'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4 mt-2">
          {/* Amount + ETA */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Your price (NZD)</Label>
              <div className="relative mt-1.5">
                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input type="number" value={form.amount} onChange={(e) => update('amount', e.target.value)} placeholder="0" className="pl-9" required />
              </div>
              {subtotal > 0 && <div className="text-[11px] text-muted-foreground mt-1">Line items total: ${subtotal.toFixed(2)}</div>}
            </div>
            <div>
              <Label>ETA (days from acceptance)</Label>
              <Input type="number" value={form.eta_days} onChange={(e) => update('eta_days', e.target.value)} min={1} className="mt-1.5" required />
            </div>
          </div>

          <div>
            <Label>Available start date</Label>
            <Input type="date" value={form.start_date} onChange={(e) => update('start_date', e.target.value)} className="mt-1.5" />
          </div>

          <div>
            <Label>Message to customer</Label>
            <Textarea rows={3} value={form.message} onChange={(e) => update('message', e.target.value)} placeholder="Explain your approach, experience, and value" className="mt-1.5" required />
          </div>

          {/* Line items */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <Label>Price breakdown (optional)</Label>
              <Button type="button" size="sm" variant="outline" onClick={addItem}><Plus className="w-3 h-3 mr-1" /> Add line</Button>
            </div>
            <div className="space-y-2">
              {form.line_items.map((it, i) => (
                <div key={it._key || i} className="grid grid-cols-[1fr_60px_100px_100px_28px] gap-2 items-center">
                  <Input value={it.label} onChange={(e) => updateItem(i, 'label', e.target.value)} placeholder="Item / description" />
                  <Input type="number" value={it.qty} onChange={(e) => updateItem(i, 'qty', e.target.value)} placeholder="Qty" />
                  <Input type="number" value={it.unit_price} onChange={(e) => updateItem(i, 'unit_price', e.target.value)} placeholder="Unit $" />
                  <div className="text-sm font-medium text-right pr-2">${((it.qty || 0) * (it.unit_price || 0)).toFixed(2)}</div>
                  <button type="button" onClick={() => removeItem(i)} className="text-muted-foreground hover:text-destructive p-1"><X className="w-3.5 h-3.5" /></button>
                </div>
              ))}
            </div>
          </div>

          {/* Warranty & payment */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Warranty (months)</Label>
              <Input type="number" value={form.warranty_months} onChange={(e) => update('warranty_months', e.target.value)} min={0} className="mt-1.5" />
            </div>
            <div>
              <Label>Payment terms</Label>
              <Input value={form.payment_terms} onChange={(e) => update('payment_terms', e.target.value)} className="mt-1.5" />
            </div>
          </div>

          {/* Additional terms */}
          <div>
            <Label>Additional terms & exclusions (optional)</Label>
            <Textarea rows={2} value={form.terms} onChange={(e) => update('terms', e.target.value)} placeholder="e.g. Materials extra, access required 8am-5pm, additional charges for waste removal..." className="mt-1.5" />
          </div>

          {/* Documents */}
          <div>
            <Label>Attach documents</Label>
            <div className="mt-1.5">
              <button type="button" onClick={() => fileRef.current?.click()} className="w-full border-2 border-dashed border-border rounded-lg p-4 hover:border-primary/40 hover:bg-accent transition-colors text-center">
                <Upload className="w-5 h-5 mx-auto text-muted-foreground mb-1" />
                <div className="text-sm text-foreground font-medium">Click to upload or drag files here</div>
                <div className="text-xs text-muted-foreground">Quotes, plans, certifications, product specs</div>
              </button>
              <input type="file" ref={fileRef} onChange={onFile} multiple hidden />
              {form.documents.length > 0 && (
                <div className="mt-2 space-y-1">
                  {form.documents.map((d, i) => (
                    <div key={d._key || `${d.name}-${d.size}-${i}`} className="flex items-center gap-2 p-2 rounded-lg bg-muted/40 text-sm">
                      <FileText className="w-4 h-4 text-primary shrink-0" />
                      <span className="flex-1 truncate">{d.name}</span>
                      <span className="text-xs text-muted-foreground">{d.size}</span>
                      <button type="button" onClick={() => removeDoc(i)} className="text-muted-foreground hover:text-destructive"><X className="w-3.5 h-3.5" /></button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Terms acceptance */}
          <label className="flex items-start gap-3 p-3 rounded-lg bg-muted/40 border border-border cursor-pointer">
            <Checkbox checked={form.acceptTerms} onCheckedChange={(v) => update('acceptTerms', !!v)} className="mt-0.5" />
            <div className="text-xs text-foreground/90">
              I confirm I am licensed &amp; insured for this work, that my bid is honest and complete, and I agree to Pro Finder NZ&apos;s <span className="text-primary">Provider Terms of Service</span> and <span className="text-primary">Escrow Payment Policy</span>.
            </div>
          </label>

          <div className="flex gap-3 pt-2">
            <Button type="button" variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving} className="flex-1">
              {saving ? 'Submitting...' : (isCounter ? 'Submit revision' : 'Submit bid')}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
