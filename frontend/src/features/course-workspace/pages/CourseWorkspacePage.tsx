import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageHeader } from '@/components/shared/PageHeader';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { getErrorMessage } from '@/lib/errors';
import { useAuth } from '@/contexts/AuthContext';
import type { WorkspaceInternalTab } from '../components/WorkspaceTabs';
import { WorkspaceTabs } from '../components/WorkspaceTabs';
import { WorkspaceHeader } from '../components/WorkspaceHeader';
import { WorkspaceOverview } from '../components/WorkspaceOverview';
import { WorkspaceAnnouncements } from '../components/WorkspaceAnnouncements';
import { WorkspaceResources } from '../components/WorkspaceResources';
import { WorkspaceStudents } from '../components/WorkspaceStudents';
import { WorkspaceSettings } from '../components/WorkspaceSettings';
import { WorkspaceEvents } from '../components/WorkspaceEvents';
import { WorkspaceQuestions } from '../components/WorkspaceQuestions';
import { WorkspaceAssignments } from '../components/WorkspaceEmptyTab';
import { isWorkspaceManager, useCourseWorkspace } from '../hooks/useCourseWorkspace';
import { useParams } from 'react-router-dom';

const internalTabs: WorkspaceInternalTab[] = ['overview', 'announcements', 'resources', 'assignments', 'events', 'questions', 'students', 'settings'];

function isInternalTab(value: string | null): value is WorkspaceInternalTab {
  return value !== null && internalTabs.some((tab) => tab === value);
}

export default function CourseWorkspacePage() {
  const { offeringId } = useParams<{ offeringId: string }>();
  const { role, user } = useAuth();
  const manager = isWorkspaceManager(role ?? user?.role ?? null);
  const [searchParams, setSearchParams] = useSearchParams();
  const announcementId = searchParams.get('announcement_id');
  const [activeTab, setActiveTab] = useState<WorkspaceInternalTab>(() => {
    const requested = searchParams.get('tab');
    return isInternalTab(requested) ? requested : announcementId ? 'announcements' : 'overview';
  });
  const [createRequest, setCreateRequest] = useState(0);
  const workspaceQuery = useCourseWorkspace(offeringId);

  useEffect(() => {
    if (announcementId) setActiveTab('announcements');
  }, [announcementId]);

  const changeTab = (tab: WorkspaceInternalTab) => {
    setActiveTab(tab);
    const next = new URLSearchParams(searchParams);
    next.set('tab', tab);
    next.delete('announcement_id');
    setSearchParams(next, { replace: true });
  };

  const retry = () => void workspaceQuery.refetch();

  if (!offeringId) {
    return <EmptyState title="Course offering not found" description="A course offering is required to open a workspace." />;
  }

  if (workspaceQuery.isPending) return <PageSkeleton cards={4} rows={5} />;

  if (workspaceQuery.isError || !workspaceQuery.data) {
    return (
      <div className="space-y-5" role="alert" aria-live="assertive">
        <PageHeader kicker="Course workspace" title="Could not load workspace" description="The course workspace could not be read from the server." />
        <div className="surface space-y-3 p-5"><p className="text-sm text-[var(--danger)]">{getErrorMessage(workspaceQuery.error, 'Please retry when connected.')}</p><Button variant="outline" onClick={retry} disabled={workspaceQuery.isFetching}>Try again</Button></div>
      </div>
    );
  }

  const workspace = workspaceQuery.data;
  return (
    <div className="min-w-0 space-y-5">
      <WorkspaceHeader workspace={workspace} manager={manager} />
      <WorkspaceTabs activeTab={activeTab} offeringId={offeringId} onTabChange={changeTab} />
      <div aria-live="polite">
        {activeTab === 'overview' && <WorkspaceOverview workspace={workspace} manager={manager} canManage={workspace.permissions.can_manage} onCreateAnnouncement={() => { changeTab('announcements'); setCreateRequest((value) => value + 1); }} onOpenTab={changeTab} />}
        {activeTab === 'announcements' && <WorkspaceAnnouncements offeringId={offeringId} manager={manager} canManage={workspace.permissions.can_manage} initialAnnouncementId={announcementId} createRequest={createRequest} />}
        {activeTab === 'resources' && <WorkspaceResources offeringId={offeringId} courseCode={workspace.course.course_code} manager={manager} />}
        {activeTab === 'assignments' && <WorkspaceAssignments />}
        {activeTab === 'events' && <WorkspaceEvents offeringId={offeringId} manager={manager} />}
        {activeTab === 'questions' && <WorkspaceQuestions offeringId={offeringId} manager={manager} />}
        {activeTab === 'students' && <WorkspaceStudents offeringId={offeringId} workspace={workspace} manager={manager} />}
        {activeTab === 'settings' && <WorkspaceSettings workspace={workspace} />}
      </div>
    </div>
  );
}
