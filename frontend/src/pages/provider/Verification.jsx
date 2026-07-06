import React, { useState } from 'react';
import { ShieldCheck, Upload, CheckCircle, AlertCircle, FileCheck } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';

const items = [
  { key: 'id', label: 'Government ID verified', desc: 'Passport or NZ drivers licence', done: true },
  { key: 'trade', label: 'Trade licence uploaded', desc: 'e.g. EWRB, PGDB, LBP licence number', done: true },
  { key: 'insurance', label: 'Public liability insurance', desc: 'Minimum $2M cover, current certificate', done: true },
  { key: 'company', label: 'Company registration', desc: 'NZBN or GST number', done: false },
  { key: 'references', label: 'Client references', desc: 'At least 3 verified past clients', done: true },
  { key: 'safety', label: 'H&S at Work compliance', desc: 'Site safety plan on file', done: false },
  { key: 'background', label: 'Background check', desc: 'MoJ criminal history check completed', done: true },
];

export default function Verification() {
  const [docs, setDocs] = useState(items);
  const completed = docs.filter((d) => d.done).length;
  const pct = Math.round((completed / docs.length) * 100);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2"><ShieldCheck className="w-5 h-5 text-emerald-500" /> Verification</h1>
        <p className="text-sm text-muted-foreground">Complete your profile to earn the Verified badge and get 3x more job leads</p>
      </div>

      <div className="bg-gradient-to-r from-emerald-500 to-emerald-600 rounded-2xl p-5 text-white mb-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-medium opacity-90">Verification progress</div>
            <div className="text-3xl font-bold mt-1">{pct}% complete</div>
            <div className="text-sm opacity-90 mt-1">{completed} of {docs.length} items done</div>
          </div>
          {pct === 100 && <Badge className="bg-white/20 hover:bg-white/30 text-white border-0">FULLY VERIFIED</Badge>}
        </div>
        <div className="mt-4 h-2 rounded-full bg-white/20 overflow-hidden">
          <div className="h-full bg-white" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <div className="space-y-3">
        {docs.map((d) => (
          <div key={d.key} className="bg-card border border-border rounded-2xl p-4 flex items-center justify-between">
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${d.done ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-300' : 'bg-muted text-muted-foreground'}`}>
                {d.done ? <CheckCircle className="w-5 h-5" /> : <FileCheck className="w-5 h-5" />}
              </div>
              <div>
                <div className="font-medium text-foreground">{d.label}</div>
                <div className="text-xs text-muted-foreground">{d.desc}</div>
              </div>
            </div>
            {d.done ? (
              <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">Verified</Badge>
            ) : (
              <Button size="sm" variant="outline" onClick={() => setDocs(docs.map((x) => x.key === d.key ? { ...x, done: true } : x))}>
                <Upload className="w-3.5 h-3.5 mr-1" /> Upload
              </Button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
