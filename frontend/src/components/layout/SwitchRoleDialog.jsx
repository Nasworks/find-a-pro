import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Repeat } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '../ui/dialog';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';

const ROLE_HOMES = {
  provider: '/provider/dashboard',
  property: '/property/dashboard',
  landlord: '/landlord/dashboard',
  facilities: '/facilities/dashboard',
  insurance: '/insurance/dashboard',
};

/**
 * SwitchRoleDialog
 * A sidebar button + dialog that lets the user switch account role.
 * Handles routing to the new role's home dashboard.
 */
export default function SwitchRoleDialog({ collapsed, roles }) {
  const { user, switchRole } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const pick = async (roleId) => {
    if (roleId === user?.role) { setOpen(false); return; }
    try {
      await switchRole(roleId);
      toast.success(`Switched to ${roleId}`);
      setOpen(false);
      navigate(ROLE_HOMES[roleId] || '/client-home');
    } catch {
      toast.error('Failed to switch role');
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
          <Repeat className="w-4 h-4 shrink-0" />
          {!collapsed && <span>Switch Account Type</span>}
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Switch account type</DialogTitle>
          <DialogDescription className="sr-only">Pick a different account role to switch your active dashboard.</DialogDescription>
        </DialogHeader>
        <div className="space-y-2 mt-4">
          {roles.map((r) => {
            const Icon = r.icon;
            const active = r.id === user?.role;
            return (
              <button
                key={r.id}
                data-testid={`switch-role-${r.id}`}
                onClick={() => pick(r.id)}
                className={`w-full flex items-center gap-3 p-3 rounded-xl border ${active ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'} transition-colors text-left`}
              >
                <div className={`w-10 h-10 rounded-lg ${r.color} flex items-center justify-center text-white`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className="font-medium text-foreground">{r.label}</div>
                </div>
                {active && <span className="text-xs text-primary font-medium">Current</span>}
              </button>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}
