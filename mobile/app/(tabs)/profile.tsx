import React, { useState } from 'react';
import { Alert, Pressable, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import Constants from 'expo-constants';
import { Bell, ChevronRight, LogOut, Server } from 'lucide-react-native';

import { Card, SectionHeader } from '../../src/components/Card';
import { Screen } from '../../src/components/Screen';
import { useAuth } from '../../src/hooks/useAuth';
import { useNotifications } from '../../src/hooks/usePortalData';
import { API_BASE_URL } from '../../src/lib/api';
import { initials, roleLabel } from '../../src/lib/format';

export default function ProfileScreen() {
  const user = useAuth((state) => state.user);
  const signOut = useAuth((state) => state.signOut);
  const { data } = useNotifications();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  const unread = data?.unread_count ?? 0;
  const appVersion = Constants.expoConfig?.version ?? '1.0.0';

  const confirmSignOut = () => {
    Alert.alert('Sign out?', 'You will need your identifier and password to sign back in.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign out',
        style: 'destructive',
        onPress: () => {
          setSigningOut(true);
          void signOut().finally(() => setSigningOut(false));
        },
      },
    ]);
  };

  return (
    <Screen scroll>
      <Text className="text-2xl font-bold text-slate-50">Profile</Text>

      <View className="mb-5 mt-4 flex-row items-center">
        <View className="h-16 w-16 items-center justify-center rounded-full bg-indigo-500/20">
          <Text className="text-xl font-bold text-indigo-100">{initials(user?.full_name)}</Text>
        </View>
        <View className="ml-4 flex-1">
          <Text className="text-lg font-semibold text-slate-50">{user?.full_name ?? 'Signed in'}</Text>
          <Text className="mt-0.5 text-xs text-slate-400">{roleLabel(user?.role)}</Text>
          <Text className="mt-1 text-xs text-slate-500">{user?.identifier}</Text>
        </View>
      </View>

      <SectionHeader title="Account" />
      <Card>
        <Row label="Email" value={user?.email ?? '—'} />
        <Row label="Identifier" value={user?.identifier ?? '—'} />
        <Row
          label="Status"
          value={user?.is_active ? 'Active' : 'Pending approval'}
          valueClassName={user?.is_active ? 'text-emerald-300' : 'text-amber-300'}
        />
      </Card>

      <SectionHeader title="Portal" />
      <Pressable
        accessibilityRole="button"
        onPress={() => router.push('/notifications')}
        className="mb-3 flex-row items-center justify-between rounded-2xl border border-slate-800 bg-slate-800/50 p-4 active:opacity-70"
      >
        <View className="flex-row items-center">
          <Bell color="#a5b4fc" size={18} />
          <Text className="ml-3 text-sm font-medium text-slate-100">Notifications</Text>
        </View>
        <View className="flex-row items-center">
          <Text className="mr-2 text-xs text-slate-400">
            {unread > 0 ? `${unread} unread` : 'All read'}
          </Text>
          <ChevronRight color="#64748b" size={16} />
        </View>
      </Pressable>

      <Card>
        <View className="flex-row items-center">
          <Server color="#64748b" size={16} />
          <Text className="ml-2 text-xs text-slate-400">API</Text>
        </View>
        <Text className="mt-2 text-xs text-slate-400">{API_BASE_URL}</Text>
        <Text className="mt-3 text-[11px] uppercase tracking-wide text-slate-500">App version</Text>
        <Text className="mt-1 text-xs text-slate-400">{appVersion}</Text>
      </Card>

      <Pressable
        accessibilityRole="button"
        disabled={signingOut}
        onPress={confirmSignOut}
        className={`mt-2 flex-row items-center justify-center rounded-xl py-3 ${
          signingOut ? 'bg-slate-800' : 'bg-red-500/15 active:bg-red-500/25'
        }`}
      >
        <LogOut color="#fca5a5" size={16} />
        <Text className="ml-2 text-sm font-semibold text-red-200">
          {signingOut ? 'Signing out…' : 'Sign out'}
        </Text>
      </Pressable>
    </Screen>
  );
}

function Row({
  label,
  value,
  valueClassName = 'text-slate-200',
}: {
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <View className="mb-2 flex-row items-start justify-between">
      <Text className="text-xs text-slate-400">{label}</Text>
      <Text className={`ml-4 flex-1 text-right text-xs ${valueClassName}`}>{value}</Text>
    </View>
  );
}
