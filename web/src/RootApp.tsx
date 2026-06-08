import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import App from "./App";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import TeamPage from "./pages/TeamPage";
import ProjectPage from "./pages/ProjectPage";
import { useAuthStore } from "./stores/auth";

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore();
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function RootApp() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <AuthGuard>
              <App />
            </AuthGuard>
          }
        />
        <Route
          path="/dashboard"
          element={
            <AuthGuard>
              <DashboardPage />
            </AuthGuard>
          }
        />
        <Route
          path="/team/:teamId"
          element={
            <AuthGuard>
              <TeamPage />
            </AuthGuard>
          }
        />
        <Route
          path="/project/:projectId"
          element={
            <AuthGuard>
              <ProjectPage />
            </AuthGuard>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
