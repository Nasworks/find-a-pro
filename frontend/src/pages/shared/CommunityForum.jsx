import React, { useState } from 'react';
import { MessageCircle, Users, Plus, Eye, ArrowUp, Clock } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';

const topics = [
  { id: 1, title: 'Best practices for pricing bathroom renos in 2026?', author: 'Sarah Chen Plumbing', category: 'Pricing', replies: 42, views: 812, upvotes: 156, posted: '3 hours ago', hot: true },
  { id: 2, title: 'What is a fair callout fee in Auckland right now?', author: 'MP Electrical', category: 'Pricing', replies: 28, views: 545, upvotes: 89, posted: '5 hours ago' },
  { id: 3, title: 'Anyone else seeing heat pump service demand spike?', author: 'CoolAir Solutions', category: 'Market Trends', replies: 15, views: 302, upvotes: 44, posted: '1 day ago' },
  { id: 4, title: 'Insurance requirements for renos over $30k — what are your suppliers asking?', author: 'Roofline Experts', category: 'Compliance', replies: 33, views: 618, upvotes: 91, posted: '2 days ago' },
  { id: 5, title: 'Which trade-only wholesalers give the best returns policy?', author: 'PainterPro NZ', category: 'Suppliers', replies: 21, views: 410, upvotes: 68, posted: '3 days ago' },
  { id: 6, title: 'How do you handle late-paying clients?', author: 'Rapid Repairs', category: 'Business', replies: 87, views: 1420, upvotes: 240, posted: '4 days ago', hot: true },
];

const categories = ['All', 'Pricing', 'Market Trends', 'Compliance', 'Suppliers', 'Business', 'Tools & Materials'];

export default function CommunityForum() {
  const [cat, setCat] = useState('All');
  const filtered = cat === 'All' ? topics : topics.filter((t) => t.category === cat);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2"><Users className="w-5 h-5 text-primary" /> Community Forum</h1>
          <p className="text-sm text-muted-foreground">Discuss pricing, trends & business tips with 12,000+ NZ pros</p>
        </div>
        <Button><Plus className="w-4 h-4 mr-1" /> New Post</Button>
      </div>

      <div className="flex gap-2 mb-6 overflow-x-auto scrollbar-thin pb-2">
        {categories.map((c) => (
          <button key={c} onClick={() => setCat(c)} className={`shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${cat === c ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent'}`}>{c}</button>
        ))}
      </div>

      <div className="space-y-2">
        {filtered.map((t) => (
          <div key={t.id} className="bg-card border border-border rounded-xl p-4 hover:border-primary/40 transition-colors">
            <div className="flex items-start gap-4">
              <div className="flex flex-col items-center gap-0.5 text-xs shrink-0">
                <ArrowUp className="w-4 h-4 text-muted-foreground" />
                <span className="font-bold text-foreground">{t.upvotes}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-foreground">{t.title}</span>
                  {t.hot && <Badge className="bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300">HOT</Badge>}
                  <Badge variant="secondary">{t.category}</Badge>
                </div>
                <div className="flex flex-wrap gap-3 mt-2 text-xs text-muted-foreground">
                  <span>by <span className="text-foreground font-medium">{t.author}</span></span>
                  <span className="inline-flex items-center gap-1"><MessageCircle className="w-3 h-3" /> {t.replies} replies</span>
                  <span className="inline-flex items-center gap-1"><Eye className="w-3 h-3" /> {t.views} views</span>
                  <span className="inline-flex items-center gap-1"><Clock className="w-3 h-3" /> {t.posted}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
