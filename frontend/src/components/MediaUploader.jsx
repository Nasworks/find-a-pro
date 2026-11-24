import React, { useRef, useState } from 'react';
import { Camera, Video, Images, Upload, X, Loader2, Play } from 'lucide-react';
import { toast } from 'sonner';
import api, { API } from '../lib/api';
import { useViewMode } from '../context/ViewModeContext';

const CHUNK = 5 * 1024 * 1024;
const BACKEND = API.replace(/\/api$/, '');

export const mediaSrc = (url) => (url?.startsWith('/api/') ? `${BACKEND}${url}` : url);
export const isVideo = (url) => /\.(mp4|mov|webm|m4v|3gp|avi|mkv)$/i.test(url || '');

export async function uploadFile(file, onProgress) {
  const { data: init } = await api.post('/uploads/init', { filename: file.name || 'capture', content_type: file.type, size: file.size });
  const total = Math.max(1, Math.ceil(file.size / CHUNK));
  for (let i = 0; i < total; i += 1) {
    const blob = file.slice(i * CHUNK, (i + 1) * CHUNK);
    await api.put(`/uploads/${init.upload_id}/chunk`, blob, { params: { index: i }, headers: { 'Content-Type': 'application/octet-stream' } });
    onProgress(Math.round(((i + 1) / total) * 95));
  }
  const { data } = await api.post(`/uploads/${init.upload_id}/complete`, null, { params: { total_chunks: total } });
  onProgress(100);
  return data;
}

// Phones/tablets: camera, video recorder and photo library. Desktop: files from the computer.
export const MediaUploader = ({ value = [], onChange, testid = 'media-uploader' }) => {
  const { compact } = useViewMode();
  const [pending, setPending] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const refs = { photo: useRef(null), video: useRef(null), library: useRef(null), files: useRef(null) };

  const handleFiles = async (fileList) => {
    const files = [...(fileList || [])].filter((f) => f.type.startsWith('image/') || f.type.startsWith('video/'));
    if (!files.length) return toast.error('Please choose photos or videos');
    let urls = [...value];
    for (const f of files) {
      const id = `${f.name}-${f.size}-${Date.now()}`;
      setPending((p) => [...p, { id, name: f.name, progress: 0, video: f.type.startsWith('video/') }]);
      try {
        const res = await uploadFile(f, (progress) => setPending((p) => p.map((x) => (x.id === id ? { ...x, progress } : x))));
        urls = [...urls, res.url];
        onChange(urls);
      } catch (e) {
        toast.error(e.response?.data?.detail || `Could not upload ${f.name}`);
      } finally {
        setPending((p) => p.filter((x) => x.id !== id));
      }
    }
  };

  const pick = (k) => refs[k].current?.click();
  const onInput = (e) => { handleFiles(e.target.files); e.target.value = ''; };

  return (
    <div data-testid={testid}>
      <input ref={refs.photo} type="file" accept="image/*" capture="environment" className="hidden" onChange={onInput} data-testid={`${testid}-camera-input`} />
      <input ref={refs.video} type="file" accept="video/*" capture="environment" className="hidden" onChange={onInput} data-testid={`${testid}-video-input`} />
      <input ref={refs.library} type="file" accept="image/*,video/*" multiple className="hidden" onChange={onInput} data-testid={`${testid}-library-input`} />
      <input ref={refs.files} type="file" accept="image/*,video/*" multiple className="hidden" onChange={onInput} data-testid={`${testid}-file-input`} />

      {compact ? (
        <div className="grid grid-cols-3 gap-2">
          <PickBtn icon={Camera} label="Take photo" onClick={() => pick('photo')} testid={`${testid}-take-photo`} />
          <PickBtn icon={Video} label="Record video" onClick={() => pick('video')} testid={`${testid}-record-video`} />
          <PickBtn icon={Images} label="Photo library" onClick={() => pick('library')} testid={`${testid}-library`} />
        </div>
      ) : (
        <button
          type="button"
          onClick={() => pick('files')}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
          data-testid={`${testid}-browse`}
          className={`w-full flex flex-col items-center justify-center gap-1.5 py-6 rounded-xl border-2 border-dashed transition-colors ${dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50 hover:bg-accent/40'}`}
        >
          <Upload className="w-5 h-5 text-primary" />
          <span className="text-sm font-medium text-foreground">Upload photos or videos from your computer</span>
          <span className="text-xs text-muted-foreground">Click to browse or drag files here · photos up to 25 MB, videos up to 200 MB</span>
        </button>
      )}

      {(value.length > 0 || pending.length > 0) && (
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 mt-3" data-testid={`${testid}-previews`}>
          {value.map((u) => (
            <div key={u} className="relative aspect-square rounded-lg overflow-hidden bg-muted group">
              <MediaThumb url={u} />
              <button type="button" onClick={() => onChange(value.filter((x) => x !== u))} aria-label="Remove" data-testid={`${testid}-remove`} className="absolute top-1 right-1 w-6 h-6 rounded-full bg-black/60 text-white flex items-center justify-center"><X className="w-3.5 h-3.5" /></button>
            </div>
          ))}
          {pending.map((p) => (
            <div key={p.id} className="aspect-square rounded-lg bg-muted flex flex-col items-center justify-center gap-1 text-xs text-muted-foreground" data-testid={`${testid}-uploading`}>
              <Loader2 className="w-4 h-4 animate-spin" />
              {p.progress}%
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const PickBtn = ({ icon: Icon, label, onClick, testid }) => (
  <button type="button" onClick={onClick} data-testid={testid} className="flex flex-col items-center justify-center gap-1.5 py-4 rounded-xl bg-muted hover:bg-accent active:scale-95 transition-transform text-xs font-medium text-foreground">
    <Icon className="w-5 h-5 text-primary" />
    {label}
  </button>
);

export const MediaThumb = ({ url, className = 'w-full h-full object-cover' }) => (
  isVideo(url) ? (
    <div className="relative w-full h-full">
      <video src={mediaSrc(url)} className={className} muted playsInline preload="metadata" />
      <Play className="absolute inset-0 m-auto w-6 h-6 text-white drop-shadow" />
    </div>
  ) : <img src={mediaSrc(url)} alt="" className={className} loading="lazy" />
);

export default MediaUploader;
