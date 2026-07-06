import React from 'react';
import { BookOpen, ChevronRight, MessageSquare, Phone, Mail } from 'lucide-react';
import { Button } from '../../components/ui/button';

const faqs = [
  { q: 'How do I post my first job?', a: 'Click Post a Job from the sidebar, describe what you need, choose Instant / Quotes / Bids, and providers are notified within minutes.' },
  { q: 'How does escrow payment work?', a: 'When a bid is accepted, funds are held by Dispatchr. Once you sign off the job, funds are released to the provider. If you dispute within 48h, we mediate.' },
  { q: 'Are providers verified?', a: 'All providers are ID-checked, insurance-verified and rated by past customers. Look for the shield badge on their profile.' },
  { q: 'What if the job goes wrong?', a: 'Every job includes a 12-month workmanship warranty minimum. File a Warranty Claim from your bookings and we\'ll mediate resolution in 5 business days.' },
  { q: 'Can I cancel a booking?', a: 'Free cancellation up to 24h before scheduled start. Later cancellations may incur a 20% call-out fee.' },
  { q: 'How much does Dispatchr cost customers?', a: 'It\'s free for customers to post jobs and receive quotes. You only pay the provider\'s quoted amount.' },
];

export default function GuideHelp() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2"><BookOpen className="w-5 h-5 text-primary" /> Guide & Help</h1>
        <p className="text-sm text-muted-foreground">Everything you need to get the most out of Dispatchr</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8">
        {[
          { icon: MessageSquare, t: 'Live chat', d: 'Reply in <5 min, 7am-9pm', c: 'bg-primary' },
          { icon: Phone, t: 'Phone support', d: '0800 DISPATCH (347 728)', c: 'bg-emerald-500' },
          { icon: Mail, t: 'Email us', d: 'help@dispatchr.co', c: 'bg-violet-500' },
        ].map((s) => (
          <div key={s.t} className="bg-card border border-border rounded-2xl p-4">
            <div className={`w-9 h-9 rounded-lg ${s.c} text-white flex items-center justify-center mb-2`}><s.icon className="w-4 h-4" /></div>
            <div className="font-medium text-foreground">{s.t}</div>
            <div className="text-xs text-muted-foreground">{s.d}</div>
          </div>
        ))}
      </div>

      <h2 className="text-lg font-semibold text-foreground mb-3">Frequently asked</h2>
      <div className="space-y-2">
        {faqs.map((f) => (
          <details key={f.q} className="bg-card border border-border rounded-xl group">
            <summary className="cursor-pointer p-4 font-medium text-foreground flex items-center justify-between">
              {f.q}
              <ChevronRight className="w-4 h-4 text-muted-foreground group-open:rotate-90 transition-transform" />
            </summary>
            <div className="px-4 pb-4 text-sm text-muted-foreground border-t border-border pt-3">{f.a}</div>
          </details>
        ))}
      </div>
    </div>
  );
}
