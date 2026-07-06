import React from 'react';
import { Gavel, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';

export default function MyDisputes() {
  const disputes = [];

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2"><Gavel className="w-5 h-5 text-primary" /> My Disputes</h1>
          <p className="text-sm text-muted-foreground">Track resolution of any issues raised on your bookings</p>
        </div>
        <Button>Open new dispute</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
        {[
          { l: 'Open', v: 0, icon: AlertCircle, c: 'text-amber-500' },
          { l: 'In mediation', v: 0, icon: Clock, c: 'text-blue-500' },
          { l: 'Resolved', v: 0, icon: CheckCircle, c: 'text-emerald-500' },
        ].map((s) => (
          <div key={s.l} className="bg-card border border-border rounded-2xl p-4">
            <div className="flex items-center justify-between">
              <div className="text-xs text-muted-foreground">{s.l}</div>
              <s.icon className={`w-4 h-4 ${s.c}`} />
            </div>
            <div className="text-2xl font-bold text-foreground mt-1">{s.v}</div>
          </div>
        ))}
      </div>

      <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center">
        <Gavel className="w-10 h-10 mx-auto text-muted-foreground mb-3 opacity-40" />
        <div className="font-medium text-foreground">No disputes on file</div>
        <p className="text-sm text-muted-foreground mt-1">If a booking goes wrong, open a dispute from that booking to start mediation.</p>
        <p className="text-xs text-muted-foreground mt-3">Average resolution time: <span className="text-foreground font-semibold">3.2 business days</span></p>
      </div>
    </div>
  );
}
