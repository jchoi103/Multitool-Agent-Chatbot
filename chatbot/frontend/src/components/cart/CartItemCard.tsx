import React, { useState, useEffect, useRef } from "react";
import styles from "./CartItemCard.module.css";

interface CartItemCardProps {
  sku: string;
  item: {
    name: string;
    quantity: number;
    unit_price: number;
    product_id: string;
    image?: string;
  };
  onUpdateQuantity: (sku: string, quantity: number) => void;
  onRemove: (sku: string) => void;
}

const CartItemCard: React.FC<CartItemCardProps> = ({
  sku,
  item,
  onUpdateQuantity,
  onRemove,
}) => {
  const [localQty, setLocalQty] = useState(item.quantity);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setLocalQty(item.quantity);
  }, [item.quantity]);

  useEffect(() => {
    if (localQty === item.quantity) return;

    if (debounceTimer.current) clearTimeout(debounceTimer.current);

    debounceTimer.current = setTimeout(() => {
      if (localQty > 0) {
        onUpdateQuantity(sku, localQty);
      }
    }, 500); //debounce. only cart item count after x milliseconds

    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [localQty, item.quantity, sku, onUpdateQuantity]);

  const handleChange = (newQty: number) => {
    if (newQty >= 1) setLocalQty(newQty);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value);
    if (!isNaN(value)) {
      setLocalQty(value);
    } else if (e.target.value === "") {
      setLocalQty(1);
    }
  };

  return (
    <div className={styles.card}>
      {item.image && (
        <img src={item.image} alt={item.name} className={styles.productImage} />
      )}
      <div className={styles.details}>
        <h3 className={styles.name}>{item.name}</h3>
        <p className={styles.sku}>SKU: {sku}</p>
        <p>Unit Price: ${item.unit_price.toFixed(2)}</p>
        <p>Total: ${(item.unit_price * localQty).toFixed(2)}</p>
        <div className={styles.controls}>
          <button
            onClick={() => handleChange(localQty - 1)}
            disabled={localQty <= 1}
          >
            -
          </button>
          <input
            type="number"
            min={1}
            className={styles.qtyInput}
            value={localQty}
            onChange={handleInputChange}
          />
          <button onClick={() => handleChange(localQty + 1)}>+</button>
          <button onClick={() => onRemove(sku)} className={styles.deleteBtn}>
            Remove
          </button>
        </div>
      </div>
    </div>
  );
};

export default CartItemCard;