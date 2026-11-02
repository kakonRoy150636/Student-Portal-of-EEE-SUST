import React from 'react';
import { Text, View } from 'react-native';

interface StatTileProps {
  label: string;
  value: string;
  hint?: string;
  warning?: boolean;
}

/** One dashboard counter. Two per row, so long labels stay readable. */
export function StatTile({ label, value, hint, warning = false }: StatTileProps) {
  return (
    <View
      className={`mb-3 w-[48%] rounded-2xl border p-4 ${
        warning ? 'border-amber-500/40 bg-amber-500/10' : 'border-slate-800 bg-slate-800/50'
      }`}
    >
      <Text className={`text-xs uppercase tracking-wide ${warning ? 'text-amber-300' : 'text-slate-400'}`}>
        {label}
      </Text>
      <Text className={`mt-2 text-2xl font-bold ${warning ? 'text-amber-200' : 'text-slate-50'}`}>{value}</Text>
      {hint ? <Text className="mt-1 text-xs leading-4 text-slate-400">{hint}</Text> : null}
    </View>
  );
}
