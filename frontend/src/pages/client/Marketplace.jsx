import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, ShoppingCart, Star, Truck, Tag, ChevronRight, Package } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';
import { useCart } from '../../context/CartContext';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'sonner';

const tradeCategories = [
  { id: 'All Products', name: 'All Products', icon: Package },
  { id: 'Power Tools', name: 'Power Tools', icon: null },
  { id: 'Hand Tools', name: 'Hand Tools', icon: null },
  { id: 'Equipment', name: 'Equipment', icon: null },
  { id: 'Fixings', name: 'Fixings', icon: null },
  { id: 'Materials', name: 'Materials', icon: null },
  { id: 'Plumbing', name: 'Plumbing', icon: null },
  { id: 'Electrical', name: 'Electrical', icon: null },
  { id: 'Kitsets', name: 'Kitsets', icon: null },
  { id: 'Safety & PPE', name: 'Safety & PPE', icon: null },
];

const consumerCategories = [
  { id: 'All Products', name: 'All Products' },
  { id: 'Bathroom', name: 'Bathroom' },
  { id: 'Kitchen', name: 'Kitchen' },
  { id: 'Heating & Cooling', name: 'Heating & Cooling' },
  { id: 'Plumbing', name: 'Plumbing' },
  { id: 'Electrical', name: 'Electrical' },
  { id: 'Materials', name: 'Materials' },
  { id: 'Kitsets', name: 'Kitsets' },
  { id: 'Power Tools', name: 'Power Tools' },
];

export default function Marketplace() {
  const { user } = useAuth();
  const { add, count } = useCart();
  const [products, setProducts] = useState([]);
  const [query, setQuery] = useState('');
  const [selectedCat, setSelectedCat] = useState('All Products');
  const [loading, setLoading] = useState(true);

  const isProvider = user?.role === 'provider';
  const categories = isProvider ? tradeCategories : consumerCategories;

  useEffect(() => { load(); }, []);
  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get('/products');
      setProducts(r.data);
    } finally { setLoading(false); }
  };

  const filtered = useMemo(() => products.filter((p) => {
    if (selectedCat !== 'All Products' && p.category !== selectedCat) return false;
    if (query && !p.name.toLowerCase().includes(query.toLowerCase()) && !p.brand?.toLowerCase().includes(query.toLowerCase())) return false;
    return true;
  }), [products, selectedCat, query]);

  const featured = useMemo(() => filtered.filter((p) => p.featured), [filtered]);
  const rest = useMemo(() => filtered.filter((p) => !p.featured), [filtered]);

  const onAdd = (p) => { add(p); toast.success(`${p.name} added to cart`); };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Store banner */}
      <div className={`rounded-2xl p-6 border ${isProvider ? 'bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-950/40 dark:to-orange-950/40 border-amber-200 dark:border-amber-900' : 'bg-gradient-to-br from-primary/5 to-blue-500/5 border-primary/20'} flex items-center justify-between gap-4 flex-wrap`}>
        <div className="flex items-center gap-4">
          <div className={`w-14 h-14 rounded-2xl ${isProvider ? 'bg-gradient-to-br from-amber-500 to-orange-500' : 'bg-gradient-to-br from-primary to-blue-600'} flex items-center justify-center text-white`}>
            <Package className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">{isProvider ? 'Trade Supply Co.' : 'Marketplace'}</h1>
            <p className="text-sm text-muted-foreground">
              {isProvider ? 'Tradespeople Only · Tools, Materials & Equipment' : 'Home essentials, tools & building materials'}
            </p>
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1"><Truck className="w-3 h-3" /> Free delivery over $500</span>
              <span className="inline-flex items-center gap-1"><Tag className="w-3 h-3" /> Trade account pricing</span>
              <span className="inline-flex items-center gap-1"><Star className="w-3 h-3" /> NZ supplier partnerships</span>
            </div>
          </div>
        </div>
        <Link to="/cart">
          <Button className={isProvider ? 'bg-amber-500 hover:bg-amber-600 text-white' : ''}>
            <ShoppingCart className="w-4 h-4 mr-2" /> Cart {count > 0 && <span className="ml-1 px-1.5 py-0.5 rounded-full bg-white/20 text-xs">{count}</span>}
          </Button>
        </Link>
      </div>

      {/* Search */}
      <div className="mt-6 relative max-w-2xl">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search tools, materials, brands..." className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-muted/40 border border-transparent focus:border-primary/40 focus:bg-background outline-none text-sm transition-all" />
      </div>

      {/* Category pills */}
      <div className="mt-4 flex gap-2 overflow-x-auto scrollbar-thin pb-2">
        {categories.map((c) => (
          <button key={c.id} onClick={() => setSelectedCat(c.id)} className={`shrink-0 inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-all ${selectedCat === c.id ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-muted text-muted-foreground hover:bg-accent hover:text-foreground'}`}>
            {c.icon ? <c.icon className="w-3.5 h-3.5" /> : null}
            {c.name}
          </button>
        ))}
      </div>

      {/* Featured */}
      {featured.length > 0 && selectedCat === 'All Products' && (
        <div className="mt-6">
          <div className="flex items-center gap-2 mb-3">
            <div className="text-amber-500">★</div>
            <h2 className="font-semibold text-foreground">FEATURED</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {featured.map((p) => <ProductCard key={p.product_id} product={p} onAdd={onAdd} featured />)}
          </div>
        </div>
      )}

      {/* All products */}
      <div className="mt-8">
        {selectedCat !== 'All Products' && <h2 className="text-lg font-semibold text-foreground mb-3">{selectedCat} <span className="text-sm text-muted-foreground font-normal">· {rest.length + (selectedCat === 'All Products' ? 0 : 0)} items</span></h2>}
        {loading ? (
          <div className="text-center py-16 text-muted-foreground">Loading products...</div>
        ) : filtered.length === 0 ? (
          <div className="bg-card border border-dashed border-border rounded-2xl p-12 text-center text-sm text-muted-foreground">
            <Package className="w-8 h-8 mx-auto mb-2 opacity-40" />
            No products match your search
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {(selectedCat === 'All Products' ? rest : filtered).map((p) => <ProductCard key={p.product_id} product={p} onAdd={onAdd} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function ProductCard({ product, onAdd, featured }) {
  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden group hover:shadow-lg hover:border-primary/30 transition-all flex flex-col">
      <Link to={`/marketplace/product/${product.product_id}`} className="block relative aspect-square bg-muted overflow-hidden">
        {featured && <Badge className="absolute top-2 left-2 z-10 bg-amber-500 text-white hover:bg-amber-600 gap-1"><Star className="w-3 h-3 fill-current" /> FEATURED</Badge>}
        {!featured && product.discount && <Badge className="absolute top-2 left-2 z-10 bg-rose-500 text-white hover:bg-rose-600">{product.discount}% OFF</Badge>}
        {product.trade_only && <Badge className="absolute top-2 right-2 z-10 bg-black/70 text-white hover:bg-black/80 text-[10px]">TRADE</Badge>}
        <img src={product.image} alt={product.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" onError={(e) => { e.target.src = 'https://images.unsplash.com/photo-1560184897-ae75f418493e?w=500'; }} />
      </Link>
      <div className="p-3 flex flex-col flex-1">
        {product.brand && <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">{product.brand}</div>}
        <Link to={`/marketplace/product/${product.product_id}`} className="text-sm font-medium text-foreground line-clamp-2 hover:text-primary transition-colors mt-0.5 min-h-[2.5rem]">{product.name}</Link>
        <p className="text-xs text-muted-foreground line-clamp-2 mt-1 flex-1">{product.description}</p>
        <div className="mt-2 flex items-baseline justify-between">
          <div>
            <div className="flex items-baseline gap-1">
              <span className="font-bold text-foreground">${product.price?.toFixed(2)}</span>
              {product.unit && <span className="text-xs text-muted-foreground">/{product.unit}</span>}
            </div>
            {product.original_price && <span className="text-[10px] text-muted-foreground line-through">${product.original_price}</span>}
          </div>
          <div className="text-[10px] text-muted-foreground">+GST</div>
        </div>
        <Button size="sm" onClick={() => onAdd(product)} className="w-full mt-2 h-8"><ShoppingCart className="w-3 h-3 mr-1" /> Add</Button>
      </div>
    </div>
  );
}
