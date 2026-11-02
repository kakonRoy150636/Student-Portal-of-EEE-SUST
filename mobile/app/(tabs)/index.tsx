import { View, Text, ScrollView } from 'react-native';

export default function Home() {
  return (
    <ScrollView className="flex-1 bg-slate-50 px-4 pt-12">
      <Text className="text-2xl font-bold text-slate-900 mb-2">Welcome back 👋</Text>
      <Text className="text-slate-500 mb-6">Your dashboard at a glance.</Text>
      <View className="bg-white rounded-2xl p-4 shadow-sm mb-3">
        <Text className="font-semibold text-slate-800">Attendance</Text>
        <Text className="text-slate-500 text-sm mt-1">87% this semester</Text>
      </View>
      <View className="bg-white rounded-2xl p-4 shadow-sm mb-3">
        <Text className="font-semibold text-slate-800">Enrolled courses</Text>
        <Text className="text-slate-500 text-sm mt-1">5 active</Text>
      </View>
      <View className="bg-white rounded-2xl p-4 shadow-sm">
        <Text className="font-semibold text-slate-800">Upcoming</Text>
        <Text className="text-slate-500 text-sm mt-1">EEE 311 — Mon 10:00</Text>
      </View>
    </ScrollView>
  );
}
