import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Breadcrumbs } from './components/Breadcrumbs';
import { DepartmentWatermark } from '@/components/shared/DepartmentWatermark';

export const AppLayout = () => (
  <div className="flex min-h-screen bg-[#050B14] text-slate-100 relative">
    {/* ব্যাকগ্রাউন্ড লোগো ওয়াটারমার্ক */}
    <DepartmentWatermark />

    <Sidebar />

    <div className="flex-1 flex flex-col min-w-0 z-10 relative">
      <Header />
      <main className="p-8 flex-1 overflow-y-auto max-w-7xl mx-auto w-full">
        <Breadcrumbs />
        <Outlet />
      </main>
    </div>
  </div>
);