import '../global.css';

import React, { useEffect } from 'react';
import { ActivityIndicator, Text, View } from 'react-native';
import { QueryClientProvider } from '@tanstack/react-query';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { onSessionExpired } from '../src/lib/api';
import { queryClient } from '../src/lib/queryClient';
import { useAuth } from '../src/hooks/useAuth';

/**
 * Owns the two things that must happen exactly once per launch:
 * restoring the stored session, and reacting to the API rejecting a refresh.
 *
 * Separately, it keeps the navigator honest — expo-router will happily render
 * the tab tree for a signed-out user if a deep link lands there, so the group
 * is reconciled against the auth status on every navigation.
 */
function AuthGate() {
  const status = useAuth((state) => state.status);
  const restored = useAuth((state) => state.restored);
  const restore = useAuth((state) => state.restore);
  const expireSession = useAuth((state) => state.expireSession);
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    void restore();
  }, [restore]);

  useEffect(
    () =>
      onSessionExpired(() => {
        expireSession();
      }),
    [expireSession],
  );

  useEffect(() => {
    if (!restored) return;

    const inAuthGroup = segments[0] === '(auth)';
    if (status === 'unauthenticated' && !inAuthGroup) {
      router.replace('/(auth)/login');
    } else if (status === 'authenticated' && inAuthGroup) {
      router.replace('/(tabs)');
    }
  }, [status, restored, segments, router]);

  return null;
}

function RestoringSession() {
  return (
    <View className="flex-1 items-center justify-center bg-slate-900">
      <Text className="mb-6 text-xl font-bold text-slate-100">SUST EEE Portal</Text>
      <ActivityIndicator color="#818cf8" />
      <Text className="mt-3 text-xs text-slate-400">Restoring your session…</Text>
    </View>
  );
}

export default function RootLayout() {
  const status = useAuth((state) => state.status);

  return (
    <QueryClientProvider client={queryClient}>
      <StatusBar style="light" />
      <AuthGate />
      {status === 'restoring' ? (
        <RestoringSession />
      ) : (
        <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: '#0f172a' } }}>
          <Stack.Screen name="(auth)" />
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="notifications" options={{ headerShown: true, title: 'Notifications' }} />
          <Stack.Screen name="+not-found" options={{ headerShown: true, title: 'Not found' }} />
        </Stack>
      )}
    </QueryClientProvider>
  );
}
