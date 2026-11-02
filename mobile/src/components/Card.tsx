import React from 'react';
import { Text, View } from 'react-native';

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <View className={`mb-3 rounded-2xl border border-slate-800 bg-slate-800/50 p-4 ${className}`}>
      {children}
    </View>
  );
}

interface SectionHeaderProps {
  title: string;
  detail?: string;
  action?: React.ReactNode;
}

export function SectionHeader({ title, detail, action }: SectionHeaderProps) {
  return (
    <View className="mb-3 mt-2 flex-row items-end justify-between">
      <View className="flex-1 pr-3">
        <Text className="text-base font-semibold text-slate-100">{title}</Text>
        {detail ? <Text className="mt-1 text-xs text-slate-400">{detail}</Text> : null}
      </View>
      {action}
    </View>
  );
}
