import React, { useCallback, useEffect, useState } from 'react';
import { Plus, Home as HomeIcon, Star, Pencil, Trash2, BedDouble, Bath, KeyRound } from 'lucide-react';
import { Button } from './ui/button';
import PropertyFormDialog from './PropertyFormDialog';
import api from '../lib/api';
import { toast } from 'sonner';

export const PROPERTY_ROLES = new Set(['customer', 'landlord', 'property', 'facilities']);

export default function MyPropertiesCard() {
  const [props, setProps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog] = useState({ open: false, property: null });

  const load = useCallback(() => {
    api.get('/properties/mine').then((r) => setProps(r.data || [])).catch(() => setProps([])).finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);

  const makeMain = async (p) => {
    try { await api.post(`/properties/${p.property_id}/primary`); toast.success(`${p.name || 'Property'} is now your main property`); load(); }
    catch { toast.error('Could not update'); }
  };
  const remove = async (p) => {
    if (!window.confirm(`Remove ${p.name || p.address}?`)) return;
    try { await api.delete(`/properties/${p.property_id}`); toast.success('Property removed'); load(); }
    catch { toast.error('Could not remove'); }
  };

  const main = props.find((p) => p.is_primary);
  const others = props.filter((p) => !p.is_primary);

  const renderRow = (p) => {
    const TypeIcon = HomeIcon;
    return (
      <div className={`flex items-start gap-3 p-3.5 rounded-xl border ${p.is_primary ? 'border-primary/40 bg-primary/5' : 'border-border'}`} data-testid={`property-row-${p.property_id}`}>
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${p.is_primary ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
          <TypeIcon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-foreground truncate">{p.name || (p.is_primary ? 'Main property' : 'Property')}</span>
          </div>
          <div className="text-sm text-muted-foreground truncate">{p.address}</div>
          <div className="flex flex-wrap gap-3 mt-1 text-xs text-muted-foreground">
            {p.bedrooms != null && <span className="inline-flex items-center gap-1"><BedDouble className="w-3 h-3" /> {p.bedrooms} bed</span>}
            {p.bathrooms != null && <span className="inline-flex items-center gap-1"><Bath className="w-3 h-3" /> {p.bathrooms} bath</span>}
            {p.access_notes && <span className="inline-flex items-center gap-1 min-w-0"><KeyRound className="w-3 h-3 shrink-0" /> <span className="truncate max-w-[200px]">{p.access_notes}</span></span>}
          </div>
        </div>
        <div className="flex items-center gap-0.5 shrink-0">
          {!p.is_primary && (
            <button type="button" onClick={() => makeMain(p)} data-testid={`property-make-main-${p.property_id}`} title="Make main property" className="p-2 rounded-lg text-muted-foreground hover:text-amber-500 hover:bg-accent"><Star className="w-4 h-4" /></button>
          )}
          <button type="button" onClick={() => setDialog({ open: true, property: p })} data-testid={`property-edit-${p.property_id}`} title="Edit" className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent"><Pencil className="w-4 h-4" /></button>
          <button type="button" onClick={() => remove(p)} data-testid={`property-delete-${p.property_id}`} title="Remove" className="p-2 rounded-lg text-muted-foreground hover:text-destructive hover:bg-accent"><Trash2 className="w-4 h-4" /></button>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-card border border-border rounded-2xl p-5" data-testid="my-properties-card">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div>
          <div className="font-semibold text-foreground">My properties</div>
          <div className="text-xs text-muted-foreground">Your main property and any secondary ones — pick them when you post a job.</div>
        </div>
        <Button size="sm" onClick={() => setDialog({ open: true, property: null })} data-testid="property-add"><Plus className="w-4 h-4 mr-1" /> Add</Button>
      </div>
      {loading ? null : props.length === 0 ? (
        <button type="button" onClick={() => setDialog({ open: true, property: null })} className="w-full p-6 rounded-xl border-2 border-dashed border-border text-sm text-muted-foreground hover:border-primary/40 hover:text-foreground transition-colors" data-testid="property-empty">
          <HomeIcon className="w-6 h-6 mx-auto mb-2 opacity-60" /> Add your main property
        </button>
      ) : (
        <div className="space-y-4">
          {main && (
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1"><Star className="w-3 h-3 text-amber-500" /> Main property</div>
              {renderRow(main)}
            </div>
          )}
          {others.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">Secondary properties</div>
              <div className="space-y-2">{others.map((p) => <React.Fragment key={p.property_id}>{renderRow(p)}</React.Fragment>)}</div>
            </div>
          )}
        </div>
      )}
      <PropertyFormDialog
        open={dialog.open}
        onOpenChange={(o) => setDialog((d) => ({ ...d, open: o }))}
        property={dialog.property}
        isFirst={props.length === 0}
        onSaved={load}
      />
    </div>
  );
}
