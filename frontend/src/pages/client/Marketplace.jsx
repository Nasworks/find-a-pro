import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, ShoppingCart, Tag, Truck, Zap, Menu } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';
import { useCart } from '../../context/CartContext';
import { toast } from 'sonner';

const categories = [
  { id: 'Bathroom', name: 'Bathroom', icon: '🛁' },
  { id: 'Kitchen', name: 'Kitchen', icon: '🍳' },
  { id: 'Appliances & Laundry', name: 'Appliances', icon: '🧺' },
  { id: 'Heating & Cooling', name: 'Heat/Cool', icon: '🌡️' },
  { id: 'Lighting & Electrical', name: 'Lighting', icon: '💡' },
  { id: 'Plumbing', name: 'Plumbing', icon: '🔧' },
  { id: 'Tools & Hardware', name: 'Tools', icon: '🔨' },
  { id: 'Home & Garden', name: 'Garden', icon: '🌿' },
  { id: 'Furniture', name: 'Furniture', icon: '🛋️' },
  { id: 'Flooring & Tiles', name: 'Flooring', icon: '🧱' },
  { id: 'Paint & Decorating', name: 'Paint', icon: '🎨' },
  { id: 'Smart Home', name: 'Smart', icon: '📱' },
];

export default function Marketplace() {
  const [products, setProducts] = useState([]);
  const [query, setQuery] = useState('');
  const [selectedCat, setSelectedCat] = useState(null);
  const { add } = useCart();

  const load = async () => {
    const params = {};
    if (selectedCat) params.category = selectedCat;
    if (query) params.q = query;
    const r = await api.get('/products', { params });
    setProducts(r.data);
  };
  useEffect(() => { load(); }, [selectedCat]);

  const onSearch = (e) => {
    e.preventDefault();
    load();
  };

  const onSale = products.filter((p) => p.discount);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2"><Menu className="w-5 h-5" /> Marketplace</h1>
          <p className="text-sm text-muted-foreground">Trade materials, tools & home essentials</p>
        </div>
        <Link to="/cart"><Button variant="outline"><ShoppingCart className="w-4 h-4 mr-2" /> Cart</Button></Link>
      </div>

      <form onSubmit={onSearch} className="mb-6 relative max-w-2xl">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search products, materials..." className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-muted/40 border border-transparent focus:border-primary/40 focus:bg-background outline-none text-sm transition-all" />
      </form>

      <div className="flex gap-3 overflow-x-auto pb-3 mb-6 scrollbar-thin">
        <button onClick={() => setSelectedCat(null)} className={`shrink-0 flex flex-col items-center gap-1 px-4 py-2 rounded-xl text-xs font-medium transition-colors ${!selectedCat ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-accent text-foreground'}`}>
          <span className="text-lg">🏷️</span>All
        </button>
        {categories.map((c) => (
          <button key={c.id} onClick={() => setSelectedCat(c.id)} className={`shrink-0 flex flex-col items-center gap-1 px-4 py-2 rounded-xl text-xs font-medium transition-colors ${selectedCat === c.id ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-accent text-foreground'}`}>
            <span className="text-lg">{c.icon}</span>{c.name}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <div className="p-5 rounded-2xl bg-gradient-to-r from-amber-500 to-orange-500 text-white flex items-center justify-between">
          <div>
            <Badge className="bg-white/20 text-white border-0 hover:bg-white/30">TRADE ONLY</Badge>
            <div className="text-xl font-bold mt-2">Trade Supply Store</div>
            <div className="text-sm opacity-90">Tools, materials & equipment · Free delivery $500+</div>
          </div>
          <Button variant="secondary" className="bg-white/20 hover:bg-white/30 text-white border-0">Shop Now</Button>
        </div>
        <div className="p-5 rounded-2xl bg-gradient-to-r from-rose-500 to-red-500 text-white flex items-center justify-between">
          <div>
            <Badge className="bg-white/20 text-white border-0 hover:bg-white/30">FLASH SALE</Badge>
            <div className="text-xl font-bold mt-2">Save up to 40%</div>
            <div className="text-sm opacity-90">Limited Time Offers</div>
          </div>
          <Button variant="secondary" className="bg-white/20 hover:bg-white/30 text-white border-0">Shop Now</Button>
        </div>
      </div>

      {onSale.length > 0 && !selectedCat && !query && (
        <>
          <h2 className="text-lg font-semibold text-foreground mb-3 flex items-center gap-2"><Tag className="w-4 h-4 text-primary" /> On Sale <span className="text-sm font-normal text-muted-foreground">{onSale.length} items</span></h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
            {onSale.slice(0, 10).map((p) => <ProductCard key={p.product_id} product={p} onAdd={() => { add(p); toast.success(`${p.name} added to cart`); }} />)}
          </div>
        </>
      )}

      <h2 className="text-lg font-semibold text-foreground mb-3">All Products {selectedCat && `· ${selectedCat}`}</h2>
      {products.length === 0 ? (
        <div className="bg-card border border-border rounded-2xl p-12 text-center text-sm text-muted-foreground">No products found</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {products.map((p) => <ProductCard key={p.product_id} product={p} onAdd={() => { add(p); toast.success(`${p.name} added to cart`); }} />)}
        </div>
      )}
    </div>
  );
}

function ProductCard({ product, onAdd }) {
  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden group hover:shadow-lg hover:border-primary/40 transition-all">
      <Link to={`/marketplace/product/${product.product_id}`} className="block relative aspect-square bg-muted overflow-hidden">
        {product.discount && <Badge className="absolute top-2 left-2 z-10 bg-rose-500 text-white hover:bg-rose-600">{product.discount}% OFF</Badge>}
        {product.trade_only && <Badge className="absolute top-2 right-2 z-10 bg-amber-500 text-white hover:bg-amber-600">TRADE</Badge>}
        <img src={product.image} alt={product.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" onError={(e) => { e.target.src = 'https://images.unsplash.com/photo-1560184897-ae75f418493e?w=500'; }} />
      </Link>
      <div className="p-3">
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{product.category}</div>
        <Link to={`/marketplace/product/${product.product_id}`} className="text-sm font-medium text-foreground line-clamp-2 hover:text-primary transition-colors mt-0.5">{product.name}</Link>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="font-bold text-foreground">${product.price}</span>
          {product.original_price && <span className="text-xs text-muted-foreground line-through">${product.original_price}</span>}
        </div>
        <Button size="sm" onClick={onAdd} className="w-full mt-2 h-8"><ShoppingCart className="w-3 h-3 mr-1" /> Add</Button>
      </div>
    </div>
  );
}
