import React, { useRef, useState } from 'react';
import { Send, Paperclip, Camera, Video, Images, X, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './ui/dropdown-menu';
import { uploadFile, MediaThumb } from './MediaUploader';

// Text box + photo/video attachments (camera, video recorder or library on phones).
export const ChatComposer = ({ onSend, placeholder = 'Type a message...', testid = 'chat' }) => {
  const [text, setText] = useState('');
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(0);
  const [sending, setSending] = useState(false);
  const refs = { photo: useRef(null), video: useRef(null), library: useRef(null) };

  const onPick = async (e) => {
    const list = [...(e.target.files || [])].filter((f) => f.type.startsWith('image/') || f.type.startsWith('video/'));
    e.target.value = '';
    if (!list.length) return;
    setUploading((n) => n + list.length);
    for (const f of list) {
      try {
        const res = await uploadFile(f);
        setFiles((x) => [...x, res.url]);
      } catch (err) {
        toast.error(err.response?.data?.detail || `Could not upload ${f.name}`);
      } finally { setUploading((n) => n - 1); }
    }
  };

  const send = async () => {
    if ((!text.trim() && !files.length) || uploading || sending) return;
    setSending(true);
    try {
      await onSend(text.trim(), files);
      setText(''); setFiles([]);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not send');
    } finally { setSending(false); }
  };

  return (
    <div className="border-t border-border p-3" data-testid={`${testid}-composer`}>
      <input ref={refs.photo} type="file" accept="image/*" capture="environment" className="hidden" onChange={onPick} data-testid={`${testid}-camera-input`} />
      <input ref={refs.video} type="file" accept="video/*" capture="environment" className="hidden" onChange={onPick} data-testid={`${testid}-video-input`} />
      <input ref={refs.library} type="file" accept="image/*,video/*" multiple className="hidden" onChange={onPick} data-testid={`${testid}-library-input`} />
      {(files.length > 0 || uploading > 0) && (
        <div className="flex gap-2 mb-2 overflow-x-auto" data-testid={`${testid}-pending-attachments`}>
          {files.map((u) => (
            <div key={u} className="relative w-16 h-16 rounded-lg overflow-hidden bg-muted shrink-0">
              <MediaThumb url={u} />
              <button type="button" onClick={() => setFiles((x) => x.filter((y) => y !== u))} aria-label="Remove attachment" data-testid={`${testid}-remove-attachment`} className="absolute top-0.5 right-0.5 w-5 h-5 rounded-full bg-black/60 text-white flex items-center justify-center"><X className="w-3 h-3" /></button>
            </div>
          ))}
          {uploading > 0 && <div className="w-16 h-16 rounded-lg bg-muted flex items-center justify-center shrink-0" data-testid={`${testid}-uploading`}><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>}
        </div>
      )}
      <div className="flex gap-2 items-center">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button type="button" variant="ghost" size="icon" className="rounded-full shrink-0" aria-label="Attach photo or video" data-testid={`${testid}-attach-btn`}><Paperclip className="w-4 h-4" /></Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuItem onClick={() => refs.photo.current?.click()} data-testid={`${testid}-attach-camera`}><Camera className="w-4 h-4 mr-2" /> Take photo</DropdownMenuItem>
            <DropdownMenuItem onClick={() => refs.video.current?.click()} data-testid={`${testid}-attach-video`}><Video className="w-4 h-4 mr-2" /> Record video</DropdownMenuItem>
            <DropdownMenuItem onClick={() => refs.library.current?.click()} data-testid={`${testid}-attach-library`}><Images className="w-4 h-4 mr-2" /> Photo / video library</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()} placeholder={placeholder} data-testid={`${testid}-input`} className="flex-1 min-w-0 px-4 py-2 rounded-full bg-muted/40 border border-transparent focus:border-primary/40 focus:bg-background outline-none text-sm transition-colors" />
        <Button onClick={send} disabled={(!text.trim() && !files.length) || uploading > 0 || sending} size="icon" className="rounded-full shrink-0" aria-label="Send" data-testid={`${testid}-send-btn`}><Send className="w-4 h-4" /></Button>
      </div>
    </div>
  );
};

export const AttachmentGrid = ({ urls = [], testid = 'message-attachments' }) => {
  if (!urls.length) return null;
  return (
    <div className={`grid gap-1 mb-1 ${urls.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`} data-testid={testid}>
      {urls.map((u) => (
        <a key={u} href={u.startsWith('/api/') ? `${process.env.REACT_APP_BACKEND_URL}${u}` : u} target="_blank" rel="noreferrer" className="block w-44 sm:w-52 max-w-full aspect-square rounded-lg overflow-hidden bg-black/10">
          <MediaThumb url={u} />
        </a>
      ))}
    </div>
  );
};

export default ChatComposer;
