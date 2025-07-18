export interface ProductVariant {
  sku: string;
  price: number;
  weight: number;
  length: number;
  width: number;
  stock: number;
}

export interface ProductDetailsFromAPI {
  name: string;
  description: string;
  image: string;
  variants: ProductVariant[];
}

// Example: { "prod-123": { name: "Product Name", desc: "Product Description", image: "url", variants: [...] } }
export type ProductsApiResponse = Record<string, ProductDetailsFromAPI>;

export interface Product {
  id: string;
  productName: string;
  description: string;
  image: string;
  category?: string;
  variants: ProductVariant[];
}

export interface CartItem {
  productId: string;
  productName: string;
  image: string;
  selectedVariantSku: string;
  priceAtPurchase: number;
  quantityInCart: number;
  variantDetails?: ProductVariant;
}
