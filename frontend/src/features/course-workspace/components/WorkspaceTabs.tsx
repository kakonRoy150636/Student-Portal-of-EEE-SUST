import React from 'react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

export type WorkspaceInternalTab = 'overview' | 'announcements' | 'resources' | 'assignments' | 'events' | 'questions' | 'students' | 'settings';
export type WorkspaceTab = WorkspaceInternalTab | 'attendance' | 'schedule';

interface WorkspaceTabsProps {
  activeTab: WorkspaceTab;
  offeringId: string;
  onTabChange: (tab: WorkspaceInternalTab) => void;
}

type InternalTabDefinition = { id: WorkspaceInternalTab; label: string; internal: true };
type ExternalTabDefinition = { id: 'attendance' | 'schedule'; label: string; internal: false };

const tabs: Array<InternalTabDefinition | ExternalTabDefinition> = [
  { id: 'overview', label: 'Overview', internal: true },
  { id: 'announcements', label: 'Announcements', internal: true },
  { id: 'resources', label: 'Resources', internal: true },
  { id: 'assignments', label: 'Assignments', internal: true },
  { id: 'attendance', label: 'Attendance', internal: false },
  { id: 'schedule', label: 'Schedule', internal: false },
  { id: 'events', label: 'Events', internal: true },
  { id: 'questions', label: 'Questions', internal: true },
  { id: 'students', label: 'Students', internal: true },
  { id: 'settings', label: 'Settings', internal: true },
];

function contextualPath(tab: 'attendance' | 'schedule', offeringId: string): string {
  return `/${tab}?offeringId=${encodeURIComponent(offeringId)}`;
}

export function WorkspaceTabs({ activeTab, offeringId, onTabChange }: WorkspaceTabsProps) {
  return (
    <nav aria-label="Course workspace sections" className="min-w-0 border-b border-[var(--border)]">
      <div role="tablist" aria-label="Course workspace tabs" className="flex min-w-max gap-1 overflow-x-auto py-1">
        {tabs.map((tab) => {
          const selected = activeTab === tab.id;
          const className = cn(
            'inline-flex min-h-10 items-center whitespace-nowrap rounded-lg px-3 text-sm font-semibold transition-colors',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]',
            selected
              ? 'bg-[var(--accent-soft)] text-[var(--accent-bright)]'
              : 'text-[var(--text-muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--text)]',
          );

          if (tab.internal) {
            return (
              <button
                key={tab.id}
                type="button"
                id={`workspace-tab-${tab.id}`}
                role="tab"
                aria-selected={selected}
                aria-controls={`workspace-panel-${tab.id}`}
                className={className}
                onClick={() => onTabChange(tab.id)}
              >
                {tab.label}
              </button>
            );
          }

          return (
            <Link
              key={tab.id}
              id={`workspace-tab-${tab.id}`}
              role="tab"
              aria-selected={selected}
              className={className}
              to={contextualPath(tab.id, offeringId)}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
