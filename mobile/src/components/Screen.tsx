import React from 'react';
import { RefreshControl, ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

interface ScreenProps {
  children: React.ReactNode;
  scroll?: boolean;
  refreshing?: boolean;
  onRefresh?: () => void;
  /** Extra bottom padding for screens that end in a floating action. */
  contentPaddingBottom?: number;
}

const BACKGROUND = '#0f172a';

/** Dark canvas shared by every screen, matching the web portal's slate theme. */
export function Screen({ children, scroll = false, refreshing = false, onRefresh, contentPaddingBottom = 32 }: ScreenProps) {
  if (!scroll) {
    return (
      <SafeAreaView edges={['top', 'left', 'right']} style={{ flex: 1, backgroundColor: BACKGROUND }}>
        <View className="flex-1 px-5 pt-3">{children}</View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView edges={['top', 'left', 'right']} style={{ flex: 1, backgroundColor: BACKGROUND }}>
      <ScrollView
        className="flex-1"
        contentContainerStyle={{ paddingHorizontal: 20, paddingTop: 12, paddingBottom: contentPaddingBottom }}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          onRefresh ? (
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor="#a5b4fc"
              colors={['#818cf8']}
              progressBackgroundColor="#1e293b"
            />
          ) : undefined
        }
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}
