import React from 'react';
import { Link } from 'react-router-dom';
import { Bell, ShoppingCart, Search } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';

export default function TopBar() {
  const { user } = useAuth();
  const { count } = useCart();
  const initials = (user?.name || 'U').split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase();

  return (
    <header className="h-16 bg-card border-b border-border sticky top-0 z-30 flex items-center justify-between px-4 lg:px-6">
      <div className="flex items-center gap-4 flex-1 max-w-md">
        <div className="relative flex-1 hidden md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input type="text" placeholder="Search jobs, providers, products..." className="w-full pl-9 pr-4 py-2 rounded-lg bg-muted/50 border border-transparent focus:border-primary/40 focus:bg-background outline-none text-sm transition-all" />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Link to="/cart" className="relative p-2 rounded-lg hover:bg-accent transition-colors">
          <ShoppingCart className="w-5 h-5 text-muted-foreground" />
          {count > 0 && <span className="absolute -top-0.5 -right-0.5 min-w-4 h-4 px-1 rounded-full bg-primary text-primary-foreground text-[10px] font-semibold flex items-center justify-center">{count}</span>}
        </Link>
        <button className="relative p-2 rounded-lg hover:bg-accent transition-colors">
          <Bell className="w-5 h-5 text-muted-foreground" />
          <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-primary" />
        </button>
        <Link to="/profile" className="flex items-center gap-2.5 pl-2 pr-3 py-1.5 rounded-lg hover:bg-accent transition-colors">
          {user?.picture ? (
            <img src={user.picture} alt={user.name} className="w-8 h-8 rounded-full object-cover" />
          ) : (
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-blue-600 text-white text-xs font-semibold flex items-center justify-center">{initials}</div>
          )}
          <div className="hidden sm:block text-left">
            <div className="text-sm font-medium text-foreground leading-tight">{user?.name}</div>
            <div className="text-[11px] text-muted-foreground capitalize leading-tight">{user?.role}</div>
          </div>
        </Link>
      </div>
    </header>
  );
}
