import React from 'react';
import { PageHeader } from '@/components/shared/PageHeader';
import { ChatWindow } from '../components/ChatWindow';

export default function AIAssistantPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Tools"
        title="AI academic assistant"
        description="Ask syllabus and course questions. Answers stay inside this session."
      />
      <ChatWindow />
    </div>
  );
}
