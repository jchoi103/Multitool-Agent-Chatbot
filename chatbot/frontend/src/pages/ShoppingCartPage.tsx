import React, { useState, useEffect } from 'react';
import NavigationBar from '../components/navigation/NavigationBar';
import Footer from '../components/footer/Footer';
import { getSupabaseClient } from '../utils/supabaseClient';
import styles from './pages.module.css';
import pageSpecificStyles from './ShoppingCartPage.module.css';
import CartItemCard from "../components/cart/CartItemCard";

interface CartItem {
  name: string;
  quantity: number;
  unit_price: number;
  product_id: string;
  image?: string;
}

interface ProductData {
  name: string;
  description: string;
  image: string;
  variants: Record<string, any>;
}

type ProductsApiResponse = Record<string, ProductData>;

const ShoppingCartPage: React.FC = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [cartItems, setCartItems] = useState<Record<string, CartItem>>({});
  const [products, setProducts] = useState<ProductsApiResponse>({});

  const calculateSubtotal = (items: Record<string, CartItem>) => {
    return Object.values(items).reduce((total, item) => {
      return total + item.unit_price * item.quantity;
    }, 0);
  };

  const enrichCartWithImages = (
    rawCart: Record<string, CartItem>,
    productMap: ProductsApiResponse
  ) => {
    const enrichedCart: Record<string, CartItem> = {};
    for (const [sku, item] of Object.entries(rawCart)) {
      const product = productMap[item.product_id];
      enrichedCart[sku] = {
        ...item,
        image: product?.image || "",
      };
    }
    return enrichedCart;
  };

  const handleUpdateQuantity = async (sku: string, quantity: number) => {
    if (!accessToken) return;
    try {
      const res = await fetch(`http://localhost:8000/cart/${sku}?quantity=${quantity}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
      const updatedCart = await res.json();
      const enriched = enrichCartWithImages(updatedCart, products);
      setCartItems(enriched);
    } catch (err) {
      console.error("Failed to update quantity:", err);
    }
  };

  const handleRemoveItem = async (sku: string) => {
    if (!accessToken) return;
    try {
      const res = await fetch(`http://localhost:8000/cart/${sku}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
      const updatedCart = await res.json();
      const enriched = enrichCartWithImages(updatedCart, products);
      setCartItems(enriched);
    } catch (err) {
      console.error("Error removing item:", err);
    }
  };

  const handleClearCart = async () => {
    if (!accessToken) return;
    try {
      const res = await fetch("http://localhost:8000/cart", {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
      const updatedCart = await res.json();
      const enriched = enrichCartWithImages(updatedCart, products);
      setCartItems(enriched);
    } catch (err) {
      console.error("Error clearing cart:", err);
    }
  };

  useEffect(() => {
    async function fetchInitialData() {
      try {
        const productRes = await fetch("http://localhost:8000/products");
        const productData: ProductsApiResponse = await productRes.json();
        setProducts(productData);
        const supabase = await getSupabaseClient();
        const { data } = await supabase.auth.getSession();
        const session = data.session;
        if (session) {
          setIsLoggedIn(true);
          setAccessToken(session.access_token);
          const cartRes = await fetch("http://localhost:8000/cart", {
            headers: {
              Authorization: `Bearer ${session.access_token}`,
            },
          });
          const cartData = await cartRes.json();
          const enrichedCart = enrichCartWithImages(cartData, productData);
          setCartItems(enrichedCart);
        } else {
          setIsLoggedIn(false);
        }
      } catch (err) {
        console.error("Error fetching cart or products:", err);
        setIsLoggedIn(false);
      } finally {
        setIsLoading(false);
      }
    }
    fetchInitialData();
  }, []);

  return (
    <div className={styles.pageContainer}>
      <NavigationBar />
      <main className={`${styles.pageContent} ${pageSpecificStyles.shoppingCartContent}`}>
        <h1>Your Shopping Cart</h1>

        {!isLoggedIn && !isLoading && (
          <div className={pageSpecificStyles.notLoggedIn}>
            <p>
              Please <a href="/auth?redirect=/cart">log in</a> to view your cart and add items.
            </p>
          </div>
        )}
        {isLoggedIn && isLoading && <p>Loading your cart...</p>}
        {isLoggedIn && !isLoading && Object.keys(cartItems).length === 0 && (
          <p>Your cart is empty.</p>
        )}
        {isLoggedIn && !isLoading && Object.keys(cartItems).length > 0 && (
          <div className={pageSpecificStyles.cartLayout}>
            <div className={pageSpecificStyles.leftColumn}>
              {Object.entries(cartItems).map(([sku, item]) => (
                <CartItemCard
                  key={sku}
                  sku={sku}
                  item={item}
                  onUpdateQuantity={handleUpdateQuantity}
                  onRemove={handleRemoveItem}
                />
              ))}
            </div>
            <div className={pageSpecificStyles.rightColumn}>
              <div className={pageSpecificStyles.summaryCard}>
                <h2>Summary</h2>
                <div className={pageSpecificStyles.summaryLine}>
                  <span>Subtotal</span>
                  <span>${calculateSubtotal(cartItems).toFixed(2)}</span>
                </div>
                <div className={pageSpecificStyles.summaryLine}>
                  <span>Estimated Shipping & Handling</span>
                  <span>Free</span>
                </div>
                <div className={pageSpecificStyles.summaryLine}>
                  <span>Estimated Tax</span>
                  <span>—</span>
                </div>
                <div className={pageSpecificStyles.summaryLineTotal}>
                  <span>Total</span>
                  <span>${calculateSubtotal(cartItems).toFixed(2)}</span>
                </div>
                <button className={pageSpecificStyles.checkoutButton}>Checkout</button>
                <button onClick={handleClearCart} className={styles.button}>
                  Clear Entire Cart
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
      <Footer customText={`${new Date().getFullYear()} Swish Store. Shopping Cart.`} />
    </div>
  );
};

export default ShoppingCartPage;