import { View, Text, Pressable } from 'react-native';
import { useAuth } from '@/hooks/useAuth';
import { router } from 'expo-router';

export default function Profile() {
  const { user, logout } = useAuth();
  return (
    <View className="flex-1 bg-slate-50 pt-12 px-4">
      <Text className="text-2xl font-bold text-slate-900 mb-4">Profile</Text>
      <View className="bg-white rounded-2xl p-4 shadow-sm mb-4">
        <Text className="font-semibold text-slate-800">{user?.fullName ?? 'Guest'}</Text>
        <Text className="text-slate-500 text-sm">{user?.email ?? '—'}</Text>
        <Text className="text-slate-400 text-xs mt-1">{user?.role ?? ''}</Text>
      </View>
      <Pressable className="bg-red-500 rounded-lg py-3 items-center" onPress={async () => { await logout(); router.replace('/(auth)/login'); }}>
        <Text className="text-white font-semibold">Sign out</Text>
      </Pressable>
    </View>
  );
}
