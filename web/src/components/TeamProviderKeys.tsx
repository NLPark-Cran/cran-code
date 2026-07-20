import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { KeyRound, Loader2, Trash2 } from "lucide-react";
import {
  v2Api,
  type ProviderInfo,
  type ProviderKeyRes,
} from "@/lib/api/v2";

interface TeamProviderKeysProps {
  teamId: string;
}

/**
 * Team-level provider API keys, managed by team owners/admins.
 * A team key is used when a team member has no personal key for a provider.
 */
export default function TeamProviderKeys({ teamId }: TeamProviderKeysProps) {
  const { t } = useTranslation();
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [teamKeys, setTeamKeys] = useState<ProviderKeyRes[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editorFor, setEditorFor] = useState<string | null>(null);
  const [keyInput, setKeyInput] = useState("");
  const [busy, setBusy] = useState(false);

  const fetchData = async () => {
    setError(null);
    try {
      const [providersRes, keysRes] = await Promise.all([
        v2Api.providers.list(),
        v2Api.teams.listProviderKeys(teamId),
      ]);
      setProviders(providersRes.providers);
      setTeamKeys(keysRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("providers:loadKeysFailed"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [teamId]);

  const hasTeamKey = (providerKey: string) =>
    teamKeys.some((k) => k.provider_key === providerKey && k.has_api_key);

  const handleSave = async (providerKey: string) => {
    if (!keyInput.trim()) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await v2Api.teams.putProviderKey(teamId, providerKey, keyInput.trim());
      setNotice(t("providers:teamKeySaved", { key: providerKey }));
      setEditorFor(null);
      setKeyInput("");
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("providers:saveKeyFailed"));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (providerKey: string) => {
    if (!window.confirm(t("providers:confirmRemoveTeamKey", { key: providerKey }))) {
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await v2Api.teams.deleteProviderKey(teamId, providerKey);
      setNotice(t("providers:teamKeyRemoved", { key: providerKey }));
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("providers:removeKeyFailed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="mt-8">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">{t("providers:teamKeysTitle")}</CardTitle>
        <CardDescription>
          {t("providers:teamKeysDesc")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {notice && (
          <Alert>
            <AlertDescription>{notice}</AlertDescription>
          </Alert>
        )}
        {loading ? (
          <div className="flex justify-center py-6">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : providers.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {t("providers:noneConfigured")}
          </p>
        ) : (
          providers.map((provider) => (
            <div
              key={provider.key}
              className="rounded-md border px-3 py-2 space-y-2"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <KeyRound className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="font-mono text-sm truncate">
                    {provider.key}
                  </span>
                  {hasTeamKey(provider.key) ? (
                    <Badge variant="secondary" className="shrink-0">
                      {t("providers:keySet")}
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="shrink-0">
                      {t("providers:noTeamKey")}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {editorFor !== provider.key && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setEditorFor(provider.key);
                        setKeyInput("");
                      }}
                    >
                      {hasTeamKey(provider.key) ? t("common:replace") : t("providers:setKey")}
                    </Button>
                  )}
                  {hasTeamKey(provider.key) && (
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={busy}
                      onClick={() => handleDelete(provider.key)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  )}
                </div>
              </div>
              {editorFor === provider.key && (
                <div className="flex items-center gap-2">
                  <Input
                    type="password"
                    placeholder="sk-..."
                    value={keyInput}
                    onChange={(e) => setKeyInput(e.target.value)}
                  />
                  <Button
                    size="sm"
                    disabled={busy || !keyInput.trim()}
                    onClick={() => handleSave(provider.key)}
                  >
                    {busy && (
                      <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                    )}
                    {t("common:save")}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setEditorFor(null);
                      setKeyInput("");
                    }}
                  >
                    {t("common:cancel")}
                  </Button>
                </div>
              )}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
