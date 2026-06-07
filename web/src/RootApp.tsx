import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import App from "./App";
import LoginPage from "./pages/LoginPage";
import { useAuthStore } from "./stores/auth";

export default function RootApp() {
  const { token } = useAuthStore();

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={token ? <App /> : <Navigate to="/login" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}
