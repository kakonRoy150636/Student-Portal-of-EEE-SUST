import { View, Text, FlatList } from 'react-native';

const courses = [
  { id: '1', code: 'EEE 311', title: 'Digital Signal Processing', credits: 3 },
  { id: '2', code: 'EEE 313', title: 'Power Systems I', credits: 3 },
  { id: '3', code: 'EEE 315', title: 'Microprocessors', credits: 3 },
];

export default function Courses() {
  return (
    <View className="flex-1 bg-slate-50 pt-12 px-4">
      <Text className="text-2xl font-bold text-slate-900 mb-4">My Courses</Text>
      <FlatList
        data={courses}
        keyExtractor={(c) => c.id}
        renderItem={({ item }) => (
          <View className="bg-white rounded-2xl p-4 mb-3 shadow-sm">
            <Text className="font-semibold text-slate-800">{item.code}</Text>
            <Text className="text-slate-500 text-sm">{item.title}</Text>
            <Text className="text-slate-400 text-xs mt-1">{item.credits} credits</Text>
          </View>
        )}
      />
    </View>
  );
}
