import React, { useEffect, useRef, useState } from 'react';
import { Search, MessageSquare, ChevronLeft } from 'lucide-react';
import { ChatComposer, AttachmentGrid } from '../../components/ChatComposer';
import api from '../../lib/api';
import { useAuth } from '../../context/AuthContext';

export default function Messages() {
  const [threads, setThreads] = useState([]);
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const { user } = useAuth();
  const scrollRef = useRef(null);

  const loadThreads = async () => {
    const r = await api.get('/threads');
    setThreads(r.data);
    if (r.data.length && !selected && window.innerWidth >= 768) setSelected(r.data[0]);
  };

  const loadMessages = async (thread_id) => {
    const r = await api.get(`/threads/${thread_id}/messages`);
    setMessages(r.data.messages || []);
    setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight }), 50);
  };

  useEffect(() => { loadThreads(); }, []);
  useEffect(() => { if (selected) loadMessages(selected.thread_id); }, [selected?.thread_id]);

  const send = async (content, attachments) => {
    await api.post('/messages', { thread_id: selected.thread_id, content, attachments });
    loadMessages(selected.thread_id);
    loadThreads();
  };

  const otherName = (thr) => {
    const otherId = thr.participants.find((p) => p !== user.user_id);
    return thr.participant_names?.[otherId] || 'User';
  };

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto">
      <h1 className={`text-2xl font-bold text-foreground mb-4 ${selected ? 'hidden md:block' : ''}`}>Messages</h1>
      <div className="bg-card border border-border rounded-2xl overflow-hidden grid grid-cols-1 md:grid-cols-[320px_1fr] h-[calc(100dvh-190px)] md:h-[calc(100vh-200px)]">
        <div className={`border-r border-border flex-col min-h-0 ${selected ? 'hidden md:flex' : 'flex'}`}>
          <div className="p-3 border-b border-border">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input value={query} onChange={(e) => setQuery(e.target.value)} data-testid="messages-search-input" placeholder="Search conversations..." className="w-full pl-9 pr-3 py-2 bg-muted/40 rounded-lg text-sm outline-none focus:bg-background" />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto scrollbar-thin">
            {threads.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground">
                <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-40" />
                No conversations yet
              </div>
            ) : threads.filter((t) => !query.trim() || `${otherName(t)} ${t.subject || ''} ${t.last_message || ''}`.toLowerCase().includes(query.trim().toLowerCase())).map((t) => (
              <button key={t.thread_id} data-testid={`thread-${t.thread_id}`} onClick={() => setSelected(t)} className={`w-full text-left p-3 border-b border-border hover:bg-accent transition-colors ${selected?.thread_id === t.thread_id ? 'bg-primary/5' : ''}`}>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-blue-600 text-white text-xs font-semibold flex items-center justify-center shrink-0">
                    {otherName(t).split(' ').map((s) => s[0]).slice(0, 2).join('')}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-baseline gap-2">
                      <div className="font-medium text-sm text-foreground truncate">{otherName(t)}</div>
                      <div className="text-[10px] text-muted-foreground shrink-0">{t.last_message_at ? new Date(t.last_message_at).toLocaleDateString() : ''}</div>
                    </div>
                    <div className="text-xs text-muted-foreground truncate">{t.last_message || t.subject}</div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className={`flex-col min-h-0 min-w-0 ${selected ? 'flex' : 'hidden md:flex'}`}>
          {selected ? (
            <>
              <div className="h-14 border-b border-border px-2 md:px-4 flex items-center gap-3">
                <button onClick={() => setSelected(null)} data-testid="messages-back-btn" className="md:hidden w-9 h-9 rounded-full hover:bg-accent flex items-center justify-center" aria-label="Back to conversations"><ChevronLeft className="w-5 h-5" /></button>
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary to-blue-600 text-white text-xs font-semibold flex items-center justify-center shrink-0">
                  {otherName(selected).split(' ').map((s) => s[0]).slice(0, 2).join('')}
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-medium text-foreground truncate">{otherName(selected)}</div>
                  <div className="text-xs text-muted-foreground truncate">{selected.subject}</div>
                </div>
              </div>
              <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-3 bg-muted/20">
                {messages.length === 0 && <div className="text-center text-sm text-muted-foreground py-10">Start the conversation</div>}
                {messages.map((m) => {
                  const mine = m.sender_id === user.user_id;
                  return (
                    <div key={m.message_id} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[80%] md:max-w-[70%] px-3 py-2 rounded-2xl text-sm break-words ${mine ? 'bg-primary text-primary-foreground rounded-br-sm' : 'bg-card border border-border text-foreground rounded-bl-sm'}`}>
                        <AttachmentGrid urls={m.attachments || []} />
                        {m.content && <div>{m.content}</div>}
                        <div className={`text-[10px] mt-1 ${mine ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}>{new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
              <ChatComposer onSend={send} testid="messages" />
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">Select a conversation</div>
          )}
        </div>
      </div>
    </div>
  );
}
