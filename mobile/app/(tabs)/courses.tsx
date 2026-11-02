import React from 'react';
import { Text, View } from 'react-native';

import { Card, SectionHeader } from '../../src/components/Card';
import { Screen } from '../../src/components/Screen';
import { EmptyState, ErrorState, LoadingState } from '../../src/components/StateViews';
import { useAuth } from '../../src/hooks/useAuth';
import { useActiveCredits, useMyEnrollments } from '../../src/hooks/usePortalData';
import { describeError } from '../../src/lib/errors';
import { hasEnrollments } from '../../src/lib/format';
import type { EnrollmentStatus } from '../../src/types';

const STATUS_STYLES: Record<EnrollmentStatus, { label: string; pill: string; text: string }> = {
  enrolled: { label: 'Enrolled', pill: 'bg-indigo-500/15', text: 'text-indigo-200' },
  main: { label: 'Main', pill: 'bg-emerald-500/15', text: 'text-emerald-200' },
  improvement: { label: 'Improvement', pill: 'bg-amber-500/15', text: 'text-amber-200' },
  drop: { label: 'Dropped', pill: 'bg-slate-600/30', text: 'text-slate-300' },
};

export default function CoursesScreen() {
  const user = useAuth((state) => state.user);
  const allowed = hasEnrollments(user?.role);
  const enrollments = useMyEnrollments();
  const credits = useActiveCredits();

  const reload = () => {
    void enrollments.refetch();
    void credits.refetch();
  };

  if (!allowed) {
    return (
      <Screen scroll>
        <Text className="text-2xl font-bold text-slate-50">My Courses</Text>
        <View className="mt-6">
          <EmptyState
            title="No course list for this account"
            detail="Course enrolments belong to student and CR accounts. Teaching and administrative accounts manage courses on the web portal."
          />
        </View>
      </Screen>
    );
  }

  const rows = enrollments.data ?? [];
  const active = rows.filter((row) => row.status !== 'drop');
  const totalCredits = credits.data?.active_credit_total;

  return (
    <Screen
      scroll
      refreshing={enrollments.isRefetching || credits.isRefetching}
      onRefresh={reload}
    >
      <Text className="text-2xl font-bold text-slate-50">My Courses</Text>
      <Text className="mt-1 text-sm text-slate-400">
        {active.length} active enrollment{active.length === 1 ? '' : 's'}
        {typeof totalCredits === 'number' ? ` · ${totalCredits} credit hours this semester` : ''}
      </Text>

      <View className="mt-5">
        {enrollments.isLoading ? <LoadingState label="Loading your courses…" /> : null}

        {enrollments.isError ? (
          <ErrorState message={describeError(enrollments.error)} onRetry={reload} />
        ) : null}

        {!enrollments.isLoading && !enrollments.isError && rows.length === 0 ? (
          <EmptyState
            title="No enrollments yet"
            detail="Course selection is done from the web portal. Once you are enrolled, the courses appear here."
          />
        ) : null}

        {rows.length > 0 ? <SectionHeader title="Enrollments" detail="Grouped by semester, newest first" /> : null}

        {rows.map((enrollment) => {
          const status = STATUS_STYLES[enrollment.status];
          return (
            <Card key={enrollment.id}>
              <View className="flex-row items-start justify-between">
                <View className="flex-1 pr-3">
                  <Text className="text-sm font-semibold text-slate-100">
                    {enrollment.course_code} · {enrollment.course_title}
                  </Text>
                  <Text className="mt-1 text-xs text-slate-400">
                    {enrollment.semester_title} · {enrollment.credit_hours} credits
                  </Text>
                </View>
                <View className={`rounded-full px-2 py-1 ${status.pill}`}>
                  <Text className={`text-[11px] font-semibold ${status.text}`}>{status.label}</Text>
                </View>
              </View>
            </Card>
          );
        })}
      </View>
    </Screen>
  );
}
