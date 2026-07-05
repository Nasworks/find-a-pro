import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Trash2, Minus, Plus, ShoppingCart, ArrowRight, Truck } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { useCart } from '../../context/CartContext';
import api from '../../lib/api';
import { toast } from 'sonner';
import { useState } from 'react';

export default function Cart() {
  const { items, remove, update, total, clear } = useCart();
  const navigate = useNavigate();
  const [placing, setPlacing] = useState(false);

  const shipping = total > 500 ? 0 : 25;
  const grand = total + shipping;

  const checkout = async () => {
    if (items.length === 0) return;
    setPlacing(true);
    try {
      await api.post('/orders', { items: items.map((i) => ({ product_id: i.product_id, quantity: i.quantity })), address: 'Auckland' });
      clear();
      toast.success('Order placed! Track it in your bookings.');
      navigate('/marketplace');
    } catch {
      toast.error('Order failed');
    } finally { setPlacing(false); }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-foreground mb-1 flex items-center gap-2"><ShoppingCart className="w-5 h-5" /> Cart</h1>
      <p className="text-sm text-muted-foreground mb-6">{items.length} item{items.length !== 1 ? 's' : ''} in your cart</p>

      {items.length === 0 ? (
        <div className="bg-card border border-border rounded-2xl p-12 text-center">
          <ShoppingCart className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
          <div className="text-lg font-medium text-foreground">Your cart is empty</div>
          <p className="text-sm text-muted-foreground mt-1">Browse the marketplace to find great deals.</p>
          <Link to="/marketplace"><Button className="mt-4">Shop Marketplace</Button></Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
          <div className="space-y-3">
            {items.map((i) => (
              <div key={i.product_id} className="bg-card border border-border rounded-2xl p-4 flex gap-4">
                <div className="w-20 h-20 rounded-lg bg-muted shrink-0 overflow-hidden"><img src={i.image} alt={i.name} className="w-full h-full object-cover" /></div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-foreground truncate">{i.name}</div>
                  <div className="text-sm text-muted-foreground">${i.price}</div>
                  <div className="mt-2 flex items-center gap-2">
                    <div className="inline-flex items-center border border-border rounded-lg">
                      <button onClick={() => update(i.product_id, Math.max(1, i.quantity - 1))} className="p-1.5 hover:bg-accent"><Minus className="w-3 h-3" /></button>
                      <span className="px-3 text-sm font-medium">{i.quantity}</span>
                      <button onClick={() => update(i.product_id, i.quantity + 1)} className="p-1.5 hover:bg-accent"><Plus className="w-3 h-3" /></button>
                    </div>
                    <button onClick={() => remove(i.product_id)} className="p-1.5 text-muted-foreground hover:text-destructive"><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
                <div className="font-bold text-foreground">${(i.price * i.quantity).toFixed(2)}</div>
              </div>
            ))}
          </div>

          <div className="bg-card border border-border rounded-2xl p-5 h-fit sticky top-20">
            <div className="font-semibold text-foreground mb-4">Order summary</div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">Subtotal</span><span>${total.toFixed(2)}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Shipping</span><span>{shipping === 0 ? <span className="text-emerald-600 font-medium">Free</span> : `$${shipping.toFixed(2)}`}</span></div>
              {shipping > 0 && <div className="text-xs text-muted-foreground bg-muted/50 rounded-lg p-2 flex items-center gap-2"><Truck className="w-3 h-3" /> Add ${(500 - total).toFixed(2)} more for free shipping</div>}
            </div>
            <div className="border-t border-border my-4"></div>
            <div className="flex justify-between font-bold text-lg text-foreground">
              <span>Total</span><span>${grand.toFixed(2)}</span>
            </div>
            <Button onClick={checkout} disabled={placing} size="lg" className="w-full mt-4">
              {placing ? 'Placing order...' : <>Checkout <ArrowRight className="w-4 h-4 ml-1" /></>}
            </Button>
            <div className="text-xs text-muted-foreground text-center mt-3">Secure checkout · Mock payment for MVP</div>
          </div>
        </div>
      )}
    </div>
  );
}
