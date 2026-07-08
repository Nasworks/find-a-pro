import React from 'react';
import { FileText, Shield, Scale, Download } from 'lucide-react';
import { Button } from '../../components/ui/button';

const docs = [
  { icon: Scale, title: 'Terms of Service', desc: 'Rules for using Pro Finder NZ as a customer or provider', updated: 'Updated Jun 2026' },
  { icon: Shield, title: 'Privacy Policy', desc: 'How we collect, use and protect your data (GDPR + Privacy Act NZ 2020)', updated: 'Updated Jun 2026' },
  { icon: FileText, title: 'Provider Agreement', desc: 'Terms specific to service providers, including commission and payout terms', updated: 'Updated May 2026' },
  { icon: FileText, title: 'Escrow Payment Policy', desc: 'How payments are held, released and refunded', updated: 'Updated Apr 2026' },
  { icon: FileText, title: 'Warranty Terms', desc: 'Minimum 12-month workmanship warranty, exclusions and claim procedure', updated: 'Updated Mar 2026' },
  { icon: FileText, title: 'Dispute Resolution', desc: 'Mediation process and escalation timelines', updated: 'Updated Mar 2026' },
];

export default function LegalPrivacy() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2"><Scale className="w-5 h-5 text-primary" /> Legal & Privacy</h1>
        <p className="text-sm text-muted-foreground">All the fine print, in plain English</p>
      </div>

      <div className="space-y-3">
        {docs.map((d) => (
          <div key={d.title} className="bg-card border border-border rounded-xl p-4 flex items-center justify-between hover:border-primary/40 transition-colors">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center"><d.icon className="w-4 h-4" /></div>
              <div>
                <div className="font-medium text-foreground">{d.title}</div>
                <div className="text-xs text-muted-foreground">{d.desc}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">{d.updated}</div>
              </div>
            </div>
            <Button size="sm" variant="outline"><Download className="w-3.5 h-3.5 mr-1" /> PDF</Button>
          </div>
        ))}
      </div>
    </div>
  );
}
