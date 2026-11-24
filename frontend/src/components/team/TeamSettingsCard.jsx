import React, { useEffect, useState } from 'react';
import { Satellite } from 'lucide-react';
import { toast } from 'sonner';
import { Switch } from '../ui/switch';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import api from '../../lib/api';

export const TeamSettingsCard = () => {
  const [s, setS] = useState(null);
  useEffect(() => { api.get('/team/settings').then((r) => setS(r.data)); }, []);

  const save = async (next) => {
    try {
      const { data } = await api.put('/team/settings', { auto_timesheet_gps: next.auto_timesheet_gps, geofence_m: Number(next.geofence_m) });
      setS(data);
      toast.success(data.auto_timesheet_gps ? 'Auto timesheets on' : 'Auto timesheets off');
    } catch (e) { toast.error(e.response?.data?.detail || 'Could not save'); }
  };

  if (!s) return null;
  return (
    <div className="bg-card border border-border rounded-2xl p-5 space-y-4" data-testid="team-settings-card">
      <div className="flex items-start gap-3">
        <Satellite className="w-5 h-5 text-primary mt-0.5" />
        <div className="flex-1">
          <div className="font-semibold text-foreground">Auto timesheets from GPS</div>
          <p className="text-sm text-muted-foreground mt-1">When on, an employee is clocked in automatically when their phone arrives at a job site, and clocked out when they leave. It works while the app is open on their phone. Employees always have to clock in to finish a job.</p>
        </div>
        <Switch checked={s.auto_timesheet_gps} onCheckedChange={(v) => save({ ...s, auto_timesheet_gps: v })} data-testid="auto-timesheet-switch" />
      </div>
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label className="text-xs text-muted-foreground" htmlFor="geofence-input">Counts as "on site" within (metres)</label>
          <Input id="geofence-input" type="number" min={50} max={1000} value={s.geofence_m} onChange={(e) => setS({ ...s, geofence_m: e.target.value })} className="mt-1" data-testid="geofence-input" />
        </div>
        <Button variant="outline" onClick={() => save(s)} data-testid="geofence-save-btn">Save</Button>
      </div>
    </div>
  );
};

export default TeamSettingsCard;
