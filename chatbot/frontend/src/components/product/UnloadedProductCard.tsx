import React from 'react';
import styles from './product.module.css';

const UnloadedProductCard: React.FC = () => {
  return (
    <div className={`${styles.productCard} ${styles.unloadedProductCard}`}>
      <div className={styles.unloadedImage}></div>
      <div className={styles.unloadedTextShort}></div>
      <div className={styles.unloadedTextLong}></div>
    </div>
  );
};

export default UnloadedProductCard;
