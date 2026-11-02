import React from 'react';
import { FlatList, Pressable, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { CheckCheck } from 'lucide-react-native';

import { EmptyState, ErrorState, LoadingState } from '../src/components/StateViews';
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from '../src/hooks/usePortalData';
import { describeError } from '../src/lib/errors';
import { formatTimestamp } from '../src/lib/format';
import type { PortalNotification } from '../src/types';

export default function NotificationsScreen() {
  const notifications = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const items = notifications.data?.items ?? [];
  const unread = notifications.data?.unread_count ?? 0;

  return (
    <SafeAreaView edges={['left', 'right', 'bottom']} style={{ flex: 1, backgroundColor: '#0f172a' }}>
      <View className="flex-1 px-5 pt-4">
        <View className="mb-4 flex-row items-center justify-between">
          <Text className="text-xs text-slate-400">
            {unread > 0 ? `${unread} unread` : 'You are all caught up'}
          </Text>
          <Pressable
            accessibilityRole="button"
            disabled={unread === 0 || markAllRead.isPending}
            onPress={() => markAllRead.mutate()}
            className={`flex-row items-center rounded-lg px-3 py-2 ${
              unread === 0 ? 'opacity-40' : 'bg-slate-800 active:opacity-70'
            }`}
          >
            <CheckCheck color="#a5b4fc" size={14} />
            <Text className="ml-2 text-xs font-semibold text-indigo-200">Mark all read</Text>
          </Pressable>
        </View>

        {notifications.isLoading ? <LoadingState label="Loading notifications…" /> : null}

        {notifications.isError ? (
          <ErrorState message={describeError(notifications.error)} onRetry={() => void notifications.refetch()} />
        ) : null}

        {!notifications.isLoading && !notifications.isError && items.length === 0 ? (
          <EmptyState title="Nothing here yet" detail="Class reminders, announcements and enrolment notices appear here." />
        ) : null}

        <FlatList
          data={items}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={{ paddingBottom: 24 }}
          refreshing={notifications.isRefetching}
          onRefresh={() => void notifications.refetch()}
          renderItem={({ item }) => (
            <NotificationRow
              notification={item}
              onPress={() => {
                if (!item.is_read) markRead.mutate(item.id);
              }}
            />
          )}
        />
      </View>
    </SafeAreaView>
  );
}

function NotificationRow({
  notification,
  onPress,
}: {
  notification: PortalNotification;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${notification.title}${notification.is_read ? '' : ', unread'}`}
      onPress={onPress}
      className={`mb-3 rounded-2xl border p-4 active:opacity-80 ${
        notification.is_read ? 'border-slate-800 bg-slate-800/30' : 'border-indigo-500/40 bg-indigo-500/10'
      }`}
    >
      <View className="flex-row items-start justify-between">
        <Text className="flex-1 pr-3 text-sm font-semibold text-slate-100">{notification.title}</Text>
        {!notification.is_read ? <View className="mt-1.5 h-2 w-2 rounded-full bg-indigo-400" /> : null}
      </View>
      <Text className="mt-1 text-xs leading-5 text-slate-400">{notification.body}</Text>
      <Text className="mt-2 text-[11px] text-slate-500">{formatTimestamp(notification.created_at)}</Text>
    </Pressable>
  );
}
