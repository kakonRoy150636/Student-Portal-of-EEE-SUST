import React from 'react';
import { Pressable, Text, View } from 'react-native';
import { Link, Stack } from 'expo-router';

export default function NotFoundScreen() {
  return (
    <>
      <Stack.Screen options={{ title: 'Not found' }} />
      <View className="flex-1 items-center justify-center bg-slate-900 px-6">
        <Text className="text-lg font-semibold text-slate-100">This screen does not exist</Text>
        <Text className="mt-2 text-center text-sm text-slate-400">
          The link you followed may be out of date.
        </Text>
        <Link href="/(tabs)" asChild>
          <Pressable className="mt-6 rounded-xl bg-indigo-500 px-5 py-3 active:bg-indigo-400">
            <Text className="text-sm font-semibold text-white">Back to home</Text>
          </Pressable>
        </Link>
      </View>
    </>
  );
}
