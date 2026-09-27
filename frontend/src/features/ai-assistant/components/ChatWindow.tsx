import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export const ChatWindow = () => {
  const [msg, setMsg] = useState('');
  const [chat, setChat] = useState([
    { role: 'assistant', text: 'Hello. Ask a syllabus or circuit question and I will answer from the available course material.' },
  ]);

  const handleSend = () => {
    if (!msg) return;
    setChat((prev) => [
      ...prev,
      { role: 'user', text: msg },
      { role: 'assistant', text: `Saved locally for this session: “${msg}”. The live RAG endpoint is not wired on this screen yet.` },
    ]);
    setMsg('');
  };

  return (
    <div className="surface space-y-3 p-4">
      <div className="max-h-96 space-y-2 overflow-y-auto">
        {chat.map((c, i) => (
          <div
            key={i}
            className={`max-w-sm rounded-xl px-3 py-2 text-sm ${
              c.role === 'user'
                ? 'ml-auto bg-[var(--primary)] text-[var(--primary-fg)]'
                : 'mr-auto bg-[var(--surface-muted)] text-[var(--text)]'
            }`}
          >
            {c.text}
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <Input
          value={msg}
          onChange={(event) => setMsg(event.target.value)}
          placeholder="Ask a syllabus question"
          aria-label="Ask a syllabus question"
          onKeyDown={(event) => {
            if (event.key === 'Enter') handleSend();
          }}
        />
        <Button size="sm" onClick={handleSend}>Send</Button>
      </div>
    </div>
  );
};
