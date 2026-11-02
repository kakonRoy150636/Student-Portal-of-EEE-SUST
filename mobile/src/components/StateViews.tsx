import React from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';
import { AlertCircle, Inbox } from 'lucide-react-native';

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <View className="items-center justify-center py-10">
      <ActivityIndicator color="#818cf8" />
      <Text className="mt-3 text-sm text-slate-400">{label}</Text>
    </View>
  );
}

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <View className="mb-3 rounded-2xl border border-red-500/40 bg-red-500/10 p-4">
      <View className="flex-row items-start">
        <AlertCircle color="#fca5a5" size={18} />
        <Text className="ml-2 flex-1 text-sm leading-5 text-red-200">{message}</Text>
      </View>
      {onRetry ? (
        <Pressable
          accessibilityRole="button"
          onPress={onRetry}
          className="mt-3 self-start rounded-lg bg-red-500/20 px-3 py-2 active:opacity-70"
        >
          <Text className="text-xs font-semibold text-red-100">Try again</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

interface EmptyStateProps {
  title: string;
  detail?: string;
}

export function EmptyState({ title, detail }: EmptyStateProps) {
  return (
    <View className="mb-3 items-center rounded-2xl border border-slate-800 bg-slate-800/40 px-5 py-8">
      <Inbox color="#64748b" size={24} />
      <Text className="mt-3 text-sm font-semibold text-slate-200">{title}</Text>
      {detail ? <Text className="mt-1 text-center text-xs leading-5 text-slate-400">{detail}</Text> : null}
    </View>
  );
}
