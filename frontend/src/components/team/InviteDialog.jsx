import React, { useState } from 'react';
import { Copy, Loader2, Mail } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import api from '../../lib/api';

export const InviteDialog = ({ member, onClose, onDone }) => {
  const [email, setEmail] = useState(member?.email || '');
  const [busy, setBusy] = useState(false);
  const [link, setLink] = useState(null);

  const send = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/team/${member.member_id}/invite`, { email });
      setLink(`${window.location.origin}${data.invite_path}`);
      toast.success(data.email_sent ? `Invite emailed to ${data.email}` : 'Invite link ready to share');
      onDone();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not create invite');
    } finally { setBusy(false); }
  };

  const copy = async () => {
    try { await navigator.clipboard.writeText(link); toast.success('Link copied'); } catch { toast.error('Copy the link manually'); }
  };

  return (
    <Dialog open={!!member} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="invite-dialog">
        <DialogHeader>
          <DialogTitle>Give {member?.name} a login</DialogTitle>
          <DialogDescription>They'll get an employee login to see the jobs you send, clock in on site and use the team board.</DialogDescription>
        </DialogHeader>
        {!link ? (
          <div className="space-y-3">
            <div><Label>Employee email</Label><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1.5" data-testid="invite-email-input" /></div>
            <Button onClick={send} disabled={busy || !email.includes('@')} className="w-full" data-testid="invite-send-btn">
              {busy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Mail className="w-4 h-4 mr-2" />} Send invite
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">You can also text this link to them. It works once and expires in 14 days.</p>
            <div className="flex gap-2">
              <Input readOnly value={link} data-testid="invite-link-input" />
              <Button variant="outline" onClick={copy} data-testid="invite-copy-btn"><Copy className="w-4 h-4" /></Button>
            </div>
            <Button variant="secondary" className="w-full" onClick={onClose} data-testid="invite-done-btn">Done</Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default InviteDialog;
