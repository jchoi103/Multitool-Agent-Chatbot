import { Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import ProductPage from "./pages/ProductPage";
import ShoppingCartPage from "./pages/ShoppingCartPage";
import AuthPage from "./pages/AuthPage";
import ProductDetailPage from "./pages/ProductDetailPage";
import Chatbot from "./components/chatbot/Chatbot";

import "./App.css";

function App() {
  return (
    <div className="App">
      <Toaster position="top-center" />
      <Routes>
        <Route path="/products" element={<ProductPage />} />
        <Route path="/product/:id" element={<ProductDetailPage />} />
        <Route path="/cart" element={<ShoppingCartPage />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/" element={<Navigate to="/products" />} />
      </Routes>
      <Chatbot />
    </div>
  );
}

export default App;