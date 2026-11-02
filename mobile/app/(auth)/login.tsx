import { useState } from 'react';
import { View, Text, TextInput, Pressable, ActivityIndicator } from 'react-native';
import { useAuth } from '@/hooks/useAuth';
import { router } from 'expo-router';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login, loading } = useAuth();

  const submit = async () => {
    try {
      await login(email, password);
      router.replace('/(tabs)');
    } catch (e) {
      // eslint-disable-next-line no-alert
      alert('Login failed');
    }
  };

  return (
    <View className="flex-1 justify-center px-6 bg-slate-900">
      <Text className="text-2xl font-bold text-white mb-6">SUST EEE Portal</Text>
      <TextInput
        className="bg-slate-800 text-white rounded-lg px-4 py-3 mb-3"
        placeholder="Email"
        placeholderTextColor="#94a3b8"
        autoCapitalize="none"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        className="bg-slate-800 text-white rounded-lg px-4 py-3 mb-4"
        placeholder="Password"
        placeholderTextColor="#94a3b8"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />
      <Pressable className="bg-indigo-600 rounded-lg py-3 items-center" onPress={submit} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text className="text-white font-semibold">Sign in</Text>}
      </Pressable>
    </View>
  );
}
