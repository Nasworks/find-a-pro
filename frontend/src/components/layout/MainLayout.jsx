import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-x-hidden">
          <div className="animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
