import React, { useState } from 'react';
import { Button } from '@/components/ui/button';

export const ChatWindow = () => {
  const [msg, setMsg] = useState('');
  const [chat, setChat] = useState([
    { role: 'assistant', text: 'Hello! I am your EEE Academic Copilot powered by Gemini. Ask me any syllabus or circuit derivation question.' }
  ]);

  const handleSend = () => {
    if (!msg) return;
    setChat(prev => [...prev, { role: 'user', text: msg }, { role: 'assistant', text: `Grounded answer for "${msg}": In synchronous machines, armature reaction is purely demagnetizing under zero power factor lagging load.` }]);
    setMsg('');
  };

  return (
    <div className="border rounded-lg p-4 space-y-3 bg-white dark:bg-slate-900">
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {chat.map((c, i) => (
          <div key={i} className={`p-2 rounded text-xs ${c.role === 'user' ? 'bg-emerald-600 text-white ml-auto max-w-sm' : 'bg-slate-100 dark:bg-slate-800 mr-auto max-w-sm'}`}>
            {c.text}
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input className="flex-1 border rounded px-3 py-1 text-sm dark:bg-slate-800" value={msg} onChange={e => setMsg(e.target.value)} placeholder="Ask syllabus question..." />
        <Button size="sm" onClick={handleSend}>Send</Button>
      </div>
    </div>
  );
};
