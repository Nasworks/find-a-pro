import React, { useCallback, useEffect, useRef, useState } from 'react';
import { MessagesSquare } from 'lucide-react';
import api from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import { ChatComposer, AttachmentGrid } from '../../components/ChatComposer';

export default function TeamBoard() {
  const { user } = useAuth();
  const [posts, setPosts] = useState([]);
  const scrollRef = useRef(null);

  const load = useCallback(async () => {
    const { data } = await api.get('/team/board');
    setPosts(data);
    setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight }), 50);
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [load]);

  const send = async (text, attachments) => {
    await api.post('/team/board', { text, attachments });
    load();
  };

  return (
    <div className="p-4 sm:p-6 max-w-3xl mx-auto">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-foreground">Team board</h1>
        <p className="text-sm text-muted-foreground">Messages between the company and its employees. Everyone on the team can see them.</p>
      </div>
      <div className="bg-card border border-border rounded-2xl overflow-hidden flex flex-col h-[calc(100dvh-230px)]">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3 bg-muted/20" data-testid="team-board-posts">
          {posts.length === 0 && (
            <div className="text-center text-sm text-muted-foreground py-12">
              <MessagesSquare className="w-8 h-8 mx-auto mb-2 opacity-40" />
              No posts yet. Say g'day to the team.
            </div>
          )}
          {posts.map((p) => {
            const mine = p.author_id === user.user_id;
            return (
              <div key={p.post_id} className={`flex ${mine ? 'justify-end' : 'justify-start'}`} data-testid={`team-post-${p.post_id}`}>
                <div className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm break-words ${mine ? 'bg-primary text-primary-foreground rounded-br-sm' : 'bg-card border border-border rounded-bl-sm'}`}>
                  {!mine && <div className="text-[11px] font-semibold mb-0.5">{p.author_name}{p.is_owner ? ' · Company' : ''}</div>}
                  <AttachmentGrid urls={p.attachments} testid="team-post-attachments" />
                  {p.text && <div>{p.text}</div>}
                  <div className={`text-[10px] mt-1 ${mine ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}>{new Date(p.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</div>
                </div>
              </div>
            );
          })}
        </div>
        <ChatComposer onSend={send} placeholder="Message the team..." testid="team-board" />
      </div>
    </div>
  );
}
