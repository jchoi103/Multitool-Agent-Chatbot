import React, { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import NavigationBar from "../components/navigation/NavigationBar";
import Footer from "../components/footer/Footer";
import { Product, ProductsApiResponse, ProductVariant } from "../types";
import styles from "./pages.module.css";
import pageSpecificStyles from "./ProductDetailPage.module.css";
import { getSupabaseClient } from "../utils/supabaseClient";
import { toast } from 'react-hot-toast';

const ProductDetailPage: React.FC = () => {
  const { id: productId } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const [product, setProduct] = useState<Product | null>(null);
  const [selectedVariant, setSelectedVariant] = useState<ProductVariant | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  useEffect(() => {
    async function checkAuth() {
      try {
        const supabase = await getSupabaseClient();
        const { data } = await supabase.auth.getSession();
        const session = data.session;
        if (session) {
          setIsLoggedIn(true);
          setAccessToken(session.access_token);
        } else {
          setIsLoggedIn(false);
          setAccessToken(null);
        }
      } catch (error) {
        console.error("Auth check failed:", error);
        setIsLoggedIn(false);
      }
    }

    checkAuth();
  }, []);

  useEffect(() => {
    const fetchProducts = async () => {
      setIsLoading(true);
      try {
        const response = await fetch("http://localhost:8000/products");
        const data: ProductsApiResponse = await response.json();

        const transformedProducts = Object.entries(data).map(
          ([id, details]) => ({
            id,
            productName: details.name,
            description: details.description,
            image: details.image,
            variants: details.variants,
          }),
        );

        const foundProduct = transformedProducts.find(
          (p) => p.id === productId,
        );

        if (foundProduct) {
          setProduct(foundProduct);
          // Get variant from URL or default to first variant
          const variantSku = searchParams.get("variant");
          if (variantSku && foundProduct.variants) {
            const variant = foundProduct.variants.find(v => v.sku === variantSku);
            if (variant) {
              setSelectedVariant(variant);
            } else {
              setSelectedVariant(foundProduct.variants[0]);
            }
          } else if (foundProduct.variants && foundProduct.variants.length > 0) {
            setSelectedVariant(foundProduct.variants[0]);
          } else {
            setError(`Product with ID "${productId}" has no variants listed.`);
          }
        } else {
          setError(`Product with ID "${productId}" not found.`);
        }
      } catch (e) {
        console.error("Could not fetch products:", e);
        setError(e instanceof Error ? e.message : "An unknown error occurred.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchProducts();
  }, [productId, searchParams]);

  const handleVariantSelect = (variant: ProductVariant) => {
    setSelectedVariant(variant);
    const newUrl = `/product/${productId}?variant=${variant.sku}`;
    window.history.pushState({}, '', newUrl);
  };

  const handleAddToCart = async () => {
    if (!selectedVariant) {
      toast.error('Please select a product variant.');
      return;
    }
    if (!isLoggedIn || !accessToken) {
      toast.error('Please log in to add items to your cart.');
      window.location.href = `/auth?redirect=/product/${encodeURIComponent(
        productId || ""
      )}&variant=${selectedVariant.sku}`;
      return;
    }
    try {
      const response = await fetch(
        `http://localhost:8000/cart/${selectedVariant.sku}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to add to cart.");
      }
      const data = await response.json();
      toast.success('Added item to your cart!');
      console.log("Cart updated:", data);
    } catch (error) {
      console.error("Add to cart failed:", error);
      toast.error("Something went wrong while adding to cart.");
    }
  };

  if (isLoading) {
    return (
      <div className={styles.pageContainer}>
        <NavigationBar />
        <main
          className={`${styles.pageContent} ${pageSpecificStyles.detailPageContent}`}
        >
          <p>Loading product details...</p>
        </main>
        <Footer customText="Example Swish Store. Product Details." />
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      <NavigationBar />
      <main
        className={`${styles.pageContent} ${pageSpecificStyles.detailPageContent}`}
      >
        {!product || error
          ? (
            <div className={pageSpecificStyles.notFoundContainer}>
              <h1>{error || "Product data is unavailable"}</h1>
              {error && (
                <p>
                  We couldn't find the product you were looking for or it has no
                  variants.
                </p>
              )}
              {!error && !product && (
                <p>The product data could not be loaded.</p>
              )}
            </div>
          )
          : (
            <article className={pageSpecificStyles.productDetailArticle}>
              <div className={pageSpecificStyles.productImages}>
                <img
                  src={product.image || "/placeholder.png"}
                  alt={product.productName}
                  className={pageSpecificStyles.mainImage}
                />
              </div>
              <div className={pageSpecificStyles.productInfo}>
                <h1>{product.productName}</h1>
                {product.category && (
                  <p className={pageSpecificStyles.category}>
                    Category: {product.category}
                  </p>
                )}
                <p className={pageSpecificStyles.description}>
                  {product.description}
                </p>
                <div className={pageSpecificStyles.variantSelector}>
                  <h3>Select Variant:</h3>
                  <div className={pageSpecificStyles.variantButtons}>
                    {product.variants.map((variant) => (
                      <button
                        key={variant.sku}
                        onClick={() => handleVariantSelect(variant)}
                        className={`${pageSpecificStyles.variantButton} ${selectedVariant?.sku === variant.sku
                            ? pageSpecificStyles.selected
                            : ""
                          }`}
                      >
                        {variant.sku}
                      </button>
                    ))}
                  </div>
                </div>

                {selectedVariant && (
                  <div className={pageSpecificStyles.selectedVariantDetails}>
                    <h4>Variant: {selectedVariant.sku}</h4>
                    <p>Price: ${selectedVariant.price.toFixed(2)}</p>
                    <p>
                      Stock: {selectedVariant.stock > 0
                        ? `${selectedVariant.stock} available`
                        : "Out of Stock"}
                    </p>
                    <p>Weight: {selectedVariant.weight}kg</p>
                    <p>
                      Dimensions: {selectedVariant.length}cm x{" "}
                      {selectedVariant.width}cm
                    </p>
                    <button
                      onClick={handleAddToCart}
                      disabled={selectedVariant.stock <= 0}
                      className={styles.button}
                    >
                      {selectedVariant.stock > 0
                        ? "Add to Cart"
                        : "Out of Stock"}
                    </button>
                  </div>
                )}
                {!selectedVariant && product.variants.length > 0 && (
                  <p>Please select a variant to see details.</p>
                )}
              </div>
            </article>
          )}
      </main>
      <Footer customText="Example Swish Store. Product Details." />
    </div>
  );
};

export default ProductDetailPage;