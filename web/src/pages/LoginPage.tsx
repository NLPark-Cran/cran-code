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
      <div className="absolute right-4 top-4">
        <LanguageSwitcher />
      </div>
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">{t("common:brandName")}</CardTitle>
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
