import React from 'react';
import { Pressable, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Bell, CalendarClock, MapPin } from 'lucide-react-native';

import { Card, SectionHeader } from '../../src/components/Card';
import { Screen } from '../../src/components/Screen';
import { StatTile } from '../../src/components/StatTile';
import { EmptyState, ErrorState, LoadingState } from '../../src/components/StateViews';
import { useAuth } from '../../src/hooks/useAuth';
import { useDashboardSummary } from '../../src/hooks/usePortalData';
import { summarizeDashboard } from '../../src/lib/dashboard';
import { describeError } from '../../src/lib/errors';
import { formatTimeRange, dayName } from '../../src/lib/routine';
import { roleLabel } from '../../src/lib/format';

function greeting(date: Date = new Date()): string {
  const hour = date.getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export default function HomeScreen() {
  const user = useAuth((state) => state.user);
  const router = useRouter();
  const { data, isLoading, isError, error, refetch, isRefetching } = useDashboardSummary();
  const view = summarizeDashboard(data);
  const firstName = user?.full_name?.split(' ')[0] ?? 'there';

  return (
    <Screen scroll refreshing={isRefetching} onRefresh={() => void refetch()}>
      <View className="flex-row items-start justify-between">
        <View className="flex-1 pr-3">
          <Text className="text-xs uppercase tracking-wide text-slate-400">{roleLabel(user?.role)}</Text>
          <Text className="mt-1 text-2xl font-bold text-slate-50">
            {greeting()}, {firstName}
          </Text>
          <Text className="mt-1 text-sm text-slate-400">Live figures for the current semester.</Text>
        </View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={
            view.unreadNotifications > 0
              ? `Notifications, ${view.unreadNotifications} unread`
              : 'Notifications'
          }
          onPress={() => router.push('/notifications')}
          className="rounded-full border border-slate-800 bg-slate-800/60 p-3 active:opacity-70"
        >
          <Bell color="#c7d2fe" size={20} />
          {view.unreadNotifications > 0 ? (
            <View
              className="absolute -right-1 -top-1 items-center justify-center rounded-full bg-indigo-500 px-1"
              style={{ minWidth: 18, height: 18 }}
            >
              <Text className="text-[10px] font-bold text-white">
                {view.unreadNotifications > 99 ? '99+' : view.unreadNotifications}
              </Text>
            </View>
          ) : null}
        </Pressable>
      </View>

      <View className="mt-5">
        {isLoading ? <LoadingState label="Fetching your dashboard…" /> : null}

        {isError ? (
          <ErrorState
            message={describeError(error)}
            onRetry={() => void refetch()}
          />
        ) : null}

        {data ? (
          <>
            <View className="flex-row flex-wrap justify-between">
              {view.tiles.map((tile) => (
                <StatTile
                  key={tile.key}
                  label={tile.label}
                  value={tile.value}
                  hint={tile.hint}
                  warning={tile.warning}
                />
              ))}
            </View>

            {view.role === 'student' || view.role === 'cr' ? (
              <>
                <SectionHeader
                  title={`Today · ${dayName()}`}
                  detail="Classes on your routine for today"
                />
                {view.todayClasses.length === 0 ? (
                  <EmptyState title="No classes today" detail="Your next class will appear here." />
                ) : (
                  view.todayClasses.map((entry, index) => (
                    <Card key={`${entry.course_code}-${entry.start_time ?? index}`}>
                      <View className="flex-row items-start justify-between">
                        <View className="flex-1 pr-3">
                          <Text className="text-sm font-semibold text-slate-100">{entry.course_code}</Text>
                          <Text className="mt-0.5 text-xs text-slate-400">{entry.course_title}</Text>
                        </View>
                        <CalendarClock color="#818cf8" size={18} />
                      </View>
                      <View className="mt-2 flex-row flex-wrap items-center">
                        <Text className="text-xs text-slate-300">
                          {formatTimeRange(entry.start_time, entry.end_time)}
                        </Text>
                        {entry.room_number ? (
                          <View className="ml-3 flex-row items-center">
                            <MapPin color="#64748b" size={12} />
                            <Text className="ml-1 text-xs text-slate-400">
                              {entry.room_number}
                              {entry.building ? ` · ${entry.building}` : ''}
                            </Text>
                          </View>
                        ) : null}
                      </View>
                    </Card>
                  ))
                )}
              </>
            ) : null}
          </>
        ) : null}
      </View>
    </Screen>
  );
}
