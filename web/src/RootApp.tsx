import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import App from "./App";
import { useAuthStore } from "./stores/auth";

// Lazy-load heavy pages to reduce initial bundle
const LoginPage = lazy(() => import("./pages/LoginPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const TeamPage = lazy(() => import("./pages/TeamPage"));
const ProjectPage = lazy(() => import("./pages/ProjectPage"));

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore();
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

function PageSpinner() {
  return (
    <div className="flex h-screen w-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  );
}

export default function RootApp() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageSpinner />}>
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
      </Suspense>
    </BrowserRouter>
  );
}
