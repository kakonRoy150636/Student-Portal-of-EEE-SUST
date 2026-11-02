import React, { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Lock, UserRound } from 'lucide-react-native';

import { ErrorState } from '../../src/components/StateViews';
import { API_BASE_URL } from '../../src/lib/api';
import { describeError } from '../../src/lib/errors';
import { useAuth } from '../../src/hooks/useAuth';

export default function LoginScreen() {
  const signIn = useAuth((state) => state.signIn);
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = identifier.trim().length >= 3 && password.length >= 6 && !submitting;

  const onSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await signIn(identifier, password);
      // Navigation is handled by AuthGate once the status flips.
    } catch (signInError) {
      setError(describeError(signInError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView edges={['top', 'left', 'right']} style={{ flex: 1, backgroundColor: '#0f172a' }}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={{ flex: 1 }}
      >
        <ScrollView
          contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', paddingHorizontal: 24, paddingVertical: 32 }}
          keyboardShouldPersistTaps="handled"
        >
          <Text className="text-3xl font-bold text-slate-50">SUST EEE Portal</Text>
          <Text className="mt-2 text-sm leading-5 text-slate-400">
            Sign in with the institutional identifier issued by the department — your student ID, faculty handle or
            admin username. Email addresses are not accepted here.
          </Text>

          {error ? (
            <View className="mt-5">
              <ErrorState message={error} />
            </View>
          ) : null}

          <View className="mt-6">
            <Text className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Identifier</Text>
            <View className="mb-4 flex-row items-center rounded-xl border border-slate-800 bg-slate-800/50 px-3">
              <UserRound color="#64748b" size={18} />
              <TextInput
                className="ml-3 flex-1 py-3 text-base text-slate-100"
                placeholder="e.g. 2021331001"
                placeholderTextColor="#64748b"
                autoCapitalize="none"
                autoCorrect={false}
                autoComplete="username"
                textContentType="username"
                returnKeyType="next"
                value={identifier}
                onChangeText={setIdentifier}
                editable={!submitting}
              />
            </View>

            <Text className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Password</Text>
            <View className="mb-5 flex-row items-center rounded-xl border border-slate-800 bg-slate-800/50 px-3">
              <Lock color="#64748b" size={18} />
              <TextInput
                className="ml-3 flex-1 py-3 text-base text-slate-100"
                placeholder="••••••••"
                placeholderTextColor="#64748b"
                secureTextEntry
                autoCapitalize="none"
                autoComplete="current-password"
                textContentType="password"
                returnKeyType="go"
                value={password}
                onChangeText={setPassword}
                onSubmitEditing={onSubmit}
                editable={!submitting}
              />
            </View>

            <Pressable
              accessibilityRole="button"
              accessibilityState={{ disabled: !canSubmit }}
              disabled={!canSubmit}
              onPress={onSubmit}
              className={`items-center rounded-xl py-3 ${canSubmit ? 'bg-indigo-500 active:bg-indigo-400' : 'bg-slate-700'}`}
            >
              {submitting ? (
                <ActivityIndicator color="#ffffff" />
              ) : (
                <Text className={`text-base font-semibold ${canSubmit ? 'text-white' : 'text-slate-400'}`}>
                  Sign in
                </Text>
              )}
            </Pressable>

            <Text className="mt-4 text-center text-xs text-slate-500">
              Teacher and CR accounts need administrator approval before the first sign-in.
            </Text>
          </View>

          {__DEV__ ? (
            <View className="mt-10 rounded-xl border border-slate-800 bg-slate-800/30 p-3">
              <Text className="text-[11px] uppercase tracking-wide text-slate-500">API</Text>
              <Text className="mt-1 text-xs text-slate-400">{API_BASE_URL}</Text>
              <Text className="mt-1 text-[11px] text-slate-500">
                Override with EXPO_PUBLIC_API_BASE_URL if this is wrong.
              </Text>
            </View>
          ) : null}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
