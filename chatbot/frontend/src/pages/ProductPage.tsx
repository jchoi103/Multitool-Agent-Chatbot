import React, { useEffect, useState } from "react";
import NavigationBar from "../components/navigation/NavigationBar";
import ProductCard from "../components/product/ProductCard";
import UnloadedProductCard from "../components/product/UnloadedProductCard";
import Footer from "../components/footer/Footer";
import { Product, ProductsApiResponse } from "../types";
import styles from "./pages.module.css";
import pageSpecificStyles from "./ProductPage.module.css";

const ProductPage: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchProducts = async () => {
      setIsLoading(true);

      try {
        const response = await fetch("http://localhost:8000/products");
        const data: ProductsApiResponse = await response.json();

        const transformedProducts = Object.entries(data).map((
          [id, details],
        ) => ({
          id,
          productName: details.name,
          description: details.description,
          image: details.image,
          variants: details.variants,
        }));

        setProducts(transformedProducts);
      } catch (e) {
        console.error("cuold NOT fetch;", e);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProducts();
  }, []);

  return (
    <div className={styles.pageContainer}>
      <NavigationBar />
      <main>
        <h1 className={pageSpecificStyles.title}>Products</h1>
        <div className={pageSpecificStyles.productList}>
          {isLoading &&
            Array.from({ length: 6 }).map((_, index) => (
              <UnloadedProductCard key={index} />
            ))}
          {!isLoading &&
            products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          {!isLoading && products.length === 0 && <p>No products found.</p>}
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default ProductPage;
