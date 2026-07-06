import React, { useEffect, useState } from 'react';
import { Share2, Copy, Gift, ArrowUpRight, Users } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';
import { toast } from 'sonner';

export default function Referrals() {
  const [data, setData] = useState({ incoming: [], outgoing: [], invite_code: '', reward_per_signup: 25 });
  const [tab, setTab] = useState('incoming');

  useEffect(() => {
    api.get('/referrals/mine').then((r) => setData(r.data));
  }, []);

  const inviteLink = `https://dispatchr.co/join?code=${data.invite_code}`;
  const copy = () => { navigator.clipboard.writeText(inviteLink); toast.success('Copied to clipboard'); };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Referrals</h1>
        <p className="text-sm text-muted-foreground">Pass jobs between providers · Earn credits by inviting</p>
      </div>

      <div className="bg-gradient-to-r from-primary to-blue-600 rounded-2xl p-6 text-white">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 text-xs font-medium opacity-90"><Gift className="w-3.5 h-3.5" /> Invite & earn</div>
            <div className="text-2xl font-bold mt-2">Earn ${data.reward_per_signup} for every provider you refer</div>
            <p className="text-sm opacity-90 mt-1">They get $25 off their first month too.</p>
          </div>
          <div className="bg-white/10 backdrop-blur rounded-xl p-3 flex items-center gap-2 min-w-[280px]">
            <div className="flex-1">
              <div className="text-[10px] uppercase opacity-70">Your code</div>
              <div className="font-mono font-bold text-lg">{data.invite_code}</div>
            </div>
            <Button variant="secondary" size="sm" onClick={copy} className="bg-white/20 hover:bg-white/30 text-white border-0"><Copy className="w-3.5 h-3.5" /></Button>
          </div>
        </div>
        <div className="mt-4 flex gap-2 flex-wrap">
          <Button variant="secondary" className="bg-white/20 hover:bg-white/30 text-white border-0" onClick={copy}><Share2 className="w-4 h-4 mr-1" /> Share link</Button>
        </div>
      </div>

      <div className="border-b border-border">
        <div className="flex gap-1 -mb-px">
          <button onClick={() => setTab('incoming')} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'incoming' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>Incoming ({data.incoming.length})</button>
          <button onClick={() => setTab('outgoing')} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'outgoing' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>Passed by you ({data.outgoing.length})</button>
        </div>
      </div>

      {tab === 'incoming' && (
        <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
          <Users className="w-10 h-10 mx-auto text-muted-foreground mb-3 opacity-40" />
          <div className="font-medium text-foreground">No incoming referrals</div>
          <p className="text-sm text-muted-foreground mt-1">When another provider passes a job your way, it&apos;ll appear here with full client details.</p>
        </div>
      )}
      {tab === 'outgoing' && (
        <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
          <ArrowUpRight className="w-10 h-10 mx-auto text-muted-foreground mb-3 opacity-40" />
          <div className="font-medium text-foreground">You haven&apos;t passed any jobs</div>
          <p className="text-sm text-muted-foreground mt-1">Not the right fit for a job? Pass it to a trusted mate and earn a 10% referral fee.</p>
        </div>
      )}
    </div>
  );
}
