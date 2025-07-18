import React from 'react';
import { Link } from 'react-router-dom';
import { Product } from '../../types';
import styles from './product.module.css';

interface ProductCardProps {
  product: Product;
}

const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const displayVariant =
    product.variants && product.variants.length > 0
      ? product.variants[0]
      : null;

  return (
    <Link to={`/product/${product.id}`} className={styles.productCard}>
      <div className={styles.imageContainer}>
        <img
          src={product.image || '/placeholder.png'}
          alt={product.productName}
          className={styles.productImage}
        />
      </div>
      <div>
        <h3 className={styles.productName}>{product.productName}</h3>
        {product.category && (
          <p className={styles.productCategory}>{product.category}</p>
        )}
        {displayVariant && (
          <p className={styles.productPrice}>
            ${displayVariant.price.toFixed(2)}
          </p>
        )}
      </div>
    </Link>
  );
};

export default ProductCard;