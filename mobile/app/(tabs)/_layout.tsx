import React from 'react';
import { Tabs } from 'expo-router';
import { BookOpen, CalendarDays, Home, UserRound } from 'lucide-react-native';

import { useNotifications } from '../../src/hooks/usePortalData';

export default function TabsLayout() {
  const { data } = useNotifications();
  const unread = data?.unread_count ?? 0;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: '#a5b4fc',
        tabBarInactiveTintColor: '#64748b',
        tabBarStyle: { backgroundColor: '#111c34', borderTopColor: '#1e293b' },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Home',
          tabBarIcon: ({ color, size }) => <Home color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="courses"
        options={{
          title: 'Courses',
          tabBarIcon: ({ color, size }) => <BookOpen color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="schedule"
        options={{
          title: 'Schedule',
          tabBarIcon: ({ color, size }) => <CalendarDays color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color, size }) => <UserRound color={color} size={size} />,
          // Surfaces unread notices without adding a fifth tab.
          tabBarBadge: unread > 0 ? (unread > 99 ? '99+' : unread) : undefined,
          tabBarBadgeStyle: { backgroundColor: '#6366f1', color: '#ffffff', fontSize: 10 },
        }}
      />
    </Tabs>
  );
}
