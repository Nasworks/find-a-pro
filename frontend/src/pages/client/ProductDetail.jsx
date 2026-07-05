import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, ShoppingCart, Star, Truck, ShieldCheck, Minus, Plus } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import api from '../../lib/api';
import { useCart } from '../../context/CartContext';
import { toast } from 'sonner';

export default function ProductDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [related, setRelated] = useState([]);
  const [qty, setQty] = useState(1);
  const { add } = useCart();

  useEffect(() => {
    api.get(`/products/${id}`).then((r) => {
      setProduct(r.data);
      api.get('/products', { params: { category: r.data.category } }).then((rr) => setRelated(rr.data.filter((x) => x.product_id !== r.data.product_id).slice(0, 4)));
    });
  }, [id]);

  if (!product) return <div className="p-10 text-center text-muted-foreground">Loading...</div>;

  const doAdd = () => { add(product, qty); toast.success(`${qty} × ${product.name} added`); };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to marketplace
      </button>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
          <div className="aspect-square bg-muted relative">
            {product.discount && <Badge className="absolute top-4 left-4 z-10 bg-rose-500 text-white hover:bg-rose-600">{product.discount}% OFF</Badge>}
            <img src={product.image} alt={product.name} className="w-full h-full object-cover" />
          </div>
        </div>

        <div>
          <div className="text-xs uppercase tracking-wider text-muted-foreground">{product.category}</div>
          <h1 className="text-2xl font-bold text-foreground mt-1">{product.name}</h1>
          <div className="flex items-center gap-2 mt-2 text-sm">
            <div className="flex items-center gap-1"><Star className="w-4 h-4 fill-amber-400 text-amber-400" /> <span className="font-medium">{product.rating}</span></div>
            <span className="text-muted-foreground">({product.reviews_count} reviews)</span>
            {product.brand && <><span className="text-muted-foreground">·</span><span className="text-muted-foreground">{product.brand}</span></>}
          </div>
          <div className="mt-6 flex items-baseline gap-3">
            <span className="text-3xl font-bold text-foreground">${product.price}</span>
            {product.original_price && <span className="text-lg text-muted-foreground line-through">${product.original_price}</span>}
            {product.discount && <Badge className="bg-emerald-500 hover:bg-emerald-600">Save ${Math.round(product.original_price - product.price)}</Badge>}
          </div>
          <p className="mt-4 text-muted-foreground">{product.description}</p>

          <div className="mt-6 flex items-center gap-3">
            <div className="inline-flex items-center border border-border rounded-lg">
              <button onClick={() => setQty(Math.max(1, qty - 1))} className="p-2 hover:bg-accent rounded-l-lg"><Minus className="w-3.5 h-3.5" /></button>
              <span className="px-4 font-medium">{qty}</span>
              <button onClick={() => setQty(qty + 1)} className="p-2 hover:bg-accent rounded-r-lg"><Plus className="w-3.5 h-3.5" /></button>
            </div>
            <Button size="lg" onClick={doAdd} className="flex-1"><ShoppingCart className="w-4 h-4 mr-2" /> Add to Cart · ${(product.price * qty).toFixed(2)}</Button>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="flex items-start gap-3 p-3 rounded-xl bg-muted/40">
              <Truck className="w-5 h-5 text-primary mt-0.5" />
              <div>
                <div className="text-sm font-medium text-foreground">Fast delivery</div>
                <div className="text-xs text-muted-foreground">2–4 business days</div>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-xl bg-muted/40">
              <ShieldCheck className="w-5 h-5 text-emerald-500 mt-0.5" />
              <div>
                <div className="text-sm font-medium text-foreground">Warranty included</div>
                <div className="text-xs text-muted-foreground">Manufacturer backed</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {related.length > 0 && (
        <div className="mt-12">
          <h2 className="text-lg font-semibold text-foreground mb-4">Related products</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {related.map((p) => (
              <Link to={`/marketplace/product/${p.product_id}`} key={p.product_id} className="bg-card border border-border rounded-2xl overflow-hidden hover:shadow-md hover:border-primary/40 transition-all">
                <div className="aspect-square bg-muted"><img src={p.image} alt={p.name} className="w-full h-full object-cover" /></div>
                <div className="p-3">
                  <div className="text-sm font-medium text-foreground line-clamp-2">{p.name}</div>
                  <div className="mt-1 font-bold text-foreground">${p.price}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
