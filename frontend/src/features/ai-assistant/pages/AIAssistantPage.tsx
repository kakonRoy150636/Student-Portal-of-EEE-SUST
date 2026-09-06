import React from 'react';
import { ChatWindow } from '../components/ChatWindow';

export default function AIAssistantPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">AI Academic Assistant</h1>
      <ChatWindow />
    </div>
  );
}
