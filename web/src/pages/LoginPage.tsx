import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2 } from "lucide-react";
import { v2Api } from "@/lib/api/v2";
import { useAuthStore } from "@/stores/auth";
import LanguageSwitcher from "@/components/LanguageSwitcher";

export default function LoginPage() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { setAuth, isLoading, setLoading, error, setError } = useAuthStore();
  const [mode, setMode] = useState<"login" | "register">("login");

  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  const [regEmail, setRegEmail] = useState("");
  const [regUsername, setRegUsername] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regDisplayName, setRegDisplayName] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await v2Api.auth.login({
        email: loginEmail,
        password: loginPassword,
      });
      setAuth(res);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth:loginFailed"));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await v2Api.auth.register({
        email: regEmail,
        username: regUsername,
        password: regPassword,
        display_name: regDisplayName || undefined,
      });
      setAuth(res);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth:registerFailed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-background p-4">
      {/* Soft violet/blue brand wash over the gray canvas (CSS only) */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(80%_60%_at_50%_-10%,oklch(0.541_0.195_291/0.12),transparent_70%),radial-gradient(60%_50%_at_85%_100%,oklch(0.7_0.12_264/0.08),transparent_70%)] dark:bg-[radial-gradient(80%_60%_at_50%_-10%,oklch(0.72_0.14_291/0.10),transparent_70%),radial-gradient(60%_50%_at_85%_100%,oklch(0.6_0.15_264/0.06),transparent_70%)]"
      />
      <div className="absolute right-4 top-4 z-10">
        <LanguageSwitcher />
      </div>
      <Card className="relative z-10 w-full max-w-md rounded-2xl border-border/60 shadow-[0_1px_2px_rgba(16,24,40,0.04),0_12px_32px_-8px_rgba(16,24,40,0.10)]">
        <CardHeader className="text-center">
          <img src="/logo.png?v=2" alt="Cran" width={40} height={40} className="mx-auto mb-2 size-10" />
          <CardTitle className="bg-gradient-to-br from-[oklch(0.541_0.195_291)] to-[oklch(0.6_0.15_264)] bg-clip-text text-2xl font-bold text-transparent dark:from-[oklch(0.72_0.14_291)] dark:to-[oklch(0.75_0.12_264)]">
            {t("common:brandName")}
          </CardTitle>
          <CardDescription>{t("auth:subtitle")}</CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="flex gap-2 mb-6">
            <Button
              variant={mode === "login" ? "default" : "outline"}
              className="flex-1"
              onClick={() => { setMode("login"); setError(null); }}
            >
              {t("auth:loginTab")}
            </Button>
            <Button
              variant={mode === "register" ? "default" : "outline"}
              className="flex-1"
              onClick={() => { setMode("register"); setError(null); }}
            >
              {t("auth:registerTab")}
            </Button>
          </div>

          {mode === "login" ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <span className="text-sm font-medium">{t("auth:email")}</span>
                <Input
                  type="email"
                  placeholder="you@example.com"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <span className="text-sm font-medium">{t("auth:password")}</span>
                <Input
                  type="password"
                  placeholder="••••••••"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                {t("auth:signIn")}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="space-y-2">
                <span className="text-sm font-medium">{t("auth:email")}</span>
                <Input
                  type="email"
                  placeholder="you@example.com"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <span className="text-sm font-medium">{t("auth:username")}</span>
                <Input
                  type="text"
                  placeholder="coder123"
                  value={regUsername}
                  onChange={(e) => setRegUsername(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <span className="text-sm font-medium">{t("auth:displayNameOptional")}</span>
                <Input
                  type="text"
                  placeholder={t("auth:displayNamePlaceholder")}
                  value={regDisplayName}
                  onChange={(e) => setRegDisplayName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <span className="text-sm font-medium">{t("auth:password")}</span>
                <Input
                  type="password"
                  placeholder="••••••••"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                {t("auth:createAccount")}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
