import React from 'react';
import { Text, View } from 'react-native';
import { FlaskConical, MapPin, UserRound } from 'lucide-react-native';

import { Card } from '../../src/components/Card';
import { Screen } from '../../src/components/Screen';
import { EmptyState, ErrorState, LoadingState } from '../../src/components/StateViews';
import { useMyRoutine } from '../../src/hooks/usePortalData';
import { describeError } from '../../src/lib/errors';
import { dayName, formatTimeRange, groupRoutineByDay, todayRoutine } from '../../src/lib/routine';

export default function ScheduleScreen() {
  const routine = useMyRoutine();
  const entries = routine.data ?? [];
  const days = groupRoutineByDay(entries);
  const today = dayName().toLowerCase();
  const todayCount = todayRoutine(entries).length;

  return (
    <Screen scroll refreshing={routine.isRefetching} onRefresh={() => void routine.refetch()}>
      <Text className="text-2xl font-bold text-slate-50">Weekly Schedule</Text>
      <Text className="mt-1 text-sm text-slate-400">
        {entries.length > 0
          ? `${entries.length} class${entries.length === 1 ? '' : 'es'} a week · ${todayCount} today`
          : 'Your routine is built from your active enrolments.'}
      </Text>

      <View className="mt-5">
        {routine.isLoading ? <LoadingState label="Loading your routine…" /> : null}

        {routine.isError ? (
          <ErrorState message={describeError(routine.error)} onRetry={() => void routine.refetch()} />
        ) : null}

        {!routine.isLoading && !routine.isError && entries.length === 0 ? (
          <EmptyState
            title="No classes scheduled"
            detail="Once you are enrolled in an active semester and classes are assigned, your routine appears here."
          />
        ) : null}

        {days.map((day) => {
          const isToday = day.day.toLowerCase() === today;
          return (
            <View key={day.day} className="mb-2">
              <View className="mb-2 mt-2 flex-row items-center">
                <Text className="text-sm font-semibold text-slate-200">{day.day}</Text>
                {isToday ? (
                  <View className="ml-2 rounded-full bg-indigo-500/20 px-2 py-0.5">
                    <Text className="text-[10px] font-semibold uppercase tracking-wide text-indigo-200">Today</Text>
                  </View>
                ) : null}
              </View>

              {day.entries.map((entry) => (
                <Card key={entry.id} className="border-l-2 border-l-indigo-500/60">
                  <View className="flex-row items-start justify-between">
                    <View className="flex-1 pr-2">
                      <Text className="text-sm font-semibold text-slate-100">
                        {entry.course_code} · {entry.course_title}
                      </Text>
                      <Text className="mt-1 text-xs text-indigo-200">
                        {formatTimeRange(entry.start_time, entry.end_time)}
                      </Text>
                    </View>
                    {entry.is_lab ? (
                      <View className="flex-row items-center rounded-full bg-emerald-500/15 px-2 py-1">
                        <FlaskConical color="#6ee7b7" size={12} />
                        <Text className="ml-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-200">
                          Lab
                        </Text>
                      </View>
                    ) : null}
                  </View>

                  <View className="mt-2 flex-row flex-wrap items-center">
                    {entry.room_number ? (
                      <View className="mr-4 flex-row items-center">
                        <MapPin color="#64748b" size={12} />
                        <Text className="ml-1 text-xs text-slate-400">{entry.room_number}</Text>
                      </View>
                    ) : null}
                    {entry.instructor_name ? (
                      <View className="flex-row items-center">
                        <UserRound color="#64748b" size={12} />
                        <Text className="ml-1 text-xs text-slate-400">{entry.instructor_name}</Text>
                      </View>
                    ) : null}
                  </View>
                </Card>
              ))}
            </View>
          );
        })}
      </View>
    </Screen>
  );
}
