import React, { useState } from 'react';
import { Outlet, Link } from 'react-router-dom';
import { Bell, ShoppingCart, Menu, X } from 'lucide-react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import MobileBottomNav from './MobileBottomNav';
import Logo from '../Logo';
import ViewModeToggle from '../ViewModeToggle';
import { Sheet, SheetContent, SheetTrigger } from '../ui/sheet';
import { useViewMode } from '../../context/ViewModeContext';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';

export default function MainLayout() {
  const { isMobile } = useViewMode();
  return isMobile ? <MobileLayout /> : <DesktopLayout />;
}

function DesktopLayout() {
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

function MobileLayout() {
  return (
    <div className="mobile-viewport-wrapper">
      <div className="mobile-viewport-inner">
        <MobileTopBar />
        <main className="flex-1 overflow-y-auto overflow-x-hidden pb-20">
          <div className="animate-fade-in">
            <Outlet />
          </div>
        </main>
        <MobileBottomNav />
      </div>
    </div>
  );
}

function MobileTopBar() {
  const { user } = useAuth();
  const { count } = useCart();
  const [sideOpen, setSideOpen] = useState(false);
  const initials = (user?.name || 'U').split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase();

  return (
    <header className="sticky top-0 z-30 h-14 bg-card/95 backdrop-blur border-b border-border flex items-center justify-between px-3">
      <div className="flex items-center gap-2">
        <Sheet open={sideOpen} onOpenChange={setSideOpen}>
          <SheetTrigger asChild>
            <button data-testid="mobile-menu-btn" className="w-9 h-9 rounded-lg hover:bg-accent flex items-center justify-center" aria-label="Open menu">
              <Menu className="w-5 h-5" />
            </button>
          </SheetTrigger>
          <SheetContent side="left" className="w-[80vw] max-w-sm p-0 flex flex-col">
            <div className="p-4 border-b border-border">
              <Logo />
            </div>
            <div className="flex-1 overflow-y-auto">
              <Sidebar collapsed={false} setCollapsed={() => {}} onNavigate={() => setSideOpen(false)} embedded />
            </div>
          </SheetContent>
        </Sheet>
        <Logo showText={false} />
      </div>
      <div className="flex items-center gap-1">
        <ViewModeToggle className="w-9 h-9" />
        <Link to="/cart" className="relative w-9 h-9 rounded-lg hover:bg-accent flex items-center justify-center" aria-label="Cart">
          <ShoppingCart className="w-4 h-4 text-muted-foreground" />
          {count > 0 && <span className="absolute -top-0.5 -right-0.5 min-w-4 h-4 px-1 rounded-full bg-primary text-primary-foreground text-[10px] font-semibold flex items-center justify-center">{count}</span>}
        </Link>
        <button className="w-9 h-9 rounded-lg hover:bg-accent flex items-center justify-center relative" aria-label="Notifications">
          <Bell className="w-4 h-4 text-muted-foreground" />
          <span className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-primary" />
        </button>
        <Link to="/profile" className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-blue-600 text-white text-xs font-semibold flex items-center justify-center ml-1">{initials}</Link>
      </div>
    </header>
  );
}
