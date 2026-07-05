import React, { createContext, useContext, useEffect, useState } from 'react';

const CartContext = createContext(null);

export const CartProvider = ({ children }) => {
  const [items, setItems] = useState(() => {
    try { return JSON.parse(localStorage.getItem('dispatchr_cart') || '[]'); } catch { return []; }
  });

  useEffect(() => {
    localStorage.setItem('dispatchr_cart', JSON.stringify(items));
  }, [items]);

  const add = (product, quantity = 1) => {
    setItems((curr) => {
      const existing = curr.find((i) => i.product_id === product.product_id);
      if (existing) {
        return curr.map((i) => i.product_id === product.product_id ? { ...i, quantity: i.quantity + quantity } : i);
      }
      return [...curr, { product_id: product.product_id, name: product.name, price: product.price, image: product.image, quantity }];
    });
  };

  const remove = (product_id) => setItems((curr) => curr.filter((i) => i.product_id !== product_id));
  const update = (product_id, quantity) => setItems((curr) => curr.map((i) => i.product_id === product_id ? { ...i, quantity } : i));
  const clear = () => setItems([]);

  const total = items.reduce((s, i) => s + i.price * i.quantity, 0);
  const count = items.reduce((s, i) => s + i.quantity, 0);

  return (
    <CartContext.Provider value={{ items, add, remove, update, clear, total, count }}>
      {children}
    </CartContext.Provider>
  );
};

export const useCart = () => useContext(CartContext);
