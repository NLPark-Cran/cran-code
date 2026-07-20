import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Check,
  ChevronDown,
  KeyRound,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
  X,
} from "lucide-react";
import {
  v2Api,
  type ProviderInfo,
  type ProviderKeyRes,
  type ProviderListRes,
  type ProviderModelSpec,
  type UsageSummaryRes,
} from "@/lib/api/v2";
import { useAuthStore } from "@/stores/auth";
import Layout from "@/components/Layout";

const PROVIDER_TYPES = [
  "kimi",
  "openai_legacy",
  "openai_responses",
  "anthropic",
  "google_genai",
  "gemini",
  "vertexai",
];

const CONTEXT_TIERS = [
  { label: "256K", value: 262144 },
  { label: "512K", value: 524288 },
  { label: "1M", value: 1048576 },
];

interface ModelRow {
  model: string;
  max_context_size: string;
  capabilities: string;
  display_name: string;
}

interface FormState {
  key: string;
  type: string;
  base_url: string;
  api_key: string;
  /** null = auto-fetch on create / untouched rows */
  rows: ModelRow[] | null;
}

const EMPTY_FORM: FormState = {
  key: "",
  type: "openai_legacy",
  base_url: "",
  api_key: "",
  rows: null,
};

function formatContext(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n % 1_000_000 ? 1 : 0)}M`;
  if (n >= 1024) return `${Math.round(n / 1024)}K`;
  return String(n);
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

function rowsToSpecs(rows: ModelRow[]): ProviderModelSpec[] {
  return rows
    .filter((r) => r.model.trim())
    .map((r) => ({
      model: r.model.trim(),
      max_context_size: parseInt(r.max_context_size, 10) || 262144,
      capabilities: r.capabilities.trim()
        ? r.capabilities.split(",").map((c) => c.trim()).filter(Boolean)
        : null,
      display_name: r.display_name.trim() || null,
    }));
}

function specsToRows(specs: ProviderModelSpec[]): ModelRow[] {
  return specs.map((s) => ({
    model: s.model,
    max_context_size: String(s.max_context_size),
    capabilities: (s.capabilities ?? []).join(", "),
    display_name: s.display_name ?? "",
  }));
}

export default function ProvidersPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";

  const [data, setData] = useState<ProviderListRes | null>(null);
  const [myKeys, setMyKeys] = useState<ProviderKeyRes[]>([]);
  const [usage, setUsage] = useState<UsageSummaryRes[]>([]);
  const [usageOpen, setUsageOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectingKey, setSelectingKey] = useState<string | null>(null);
  const [thinkingBusy, setThinkingBusy] = useState(false);
  const [contextBusyKey, setContextBusyKey] = useState<string | null>(null);

  // Personal key inline editor
  const [keyEditorFor, setKeyEditorFor] = useState<string | null>(null);
  const [keyInput, setKeyInput] = useState("");
  const [keyBusy, setKeyBusy] = useState(false);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ProviderInfo | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);

  const fetchProviders = async () => {
    setError(null);
    try {
      setData(await v2Api.providers.list());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load providers");
    } finally {
      setLoading(false);
    }
  };

  const fetchMyKeys = async () => {
    try {
      setMyKeys(await v2Api.users.meProviderKeys());
    } catch {
      // Non-fatal: personal key badges just won't show.
    }
  };

  const fetchUsage = async () => {
    try {
      setUsage(await v2Api.users.meUsage());
    } catch {
      // Non-fatal.
    }
  };

  useEffect(() => {
    fetchProviders();
    fetchMyKeys();
    fetchUsage();
  }, []);

  const handleSelect = async (modelKey: string) => {
    setSelectingKey(modelKey);
    setNotice(null);
    setError(null);
    try {
      const resp = await v2Api.providers.select({ default_model: modelKey });
      const restarted = resp.restarted_session_ids?.length ?? 0;
      const skipped = resp.skipped_busy_session_ids?.length ?? 0;
      setNotice(
        `Switched default model to ${resp.default_model}. ` +
          `Restarted ${restarted} session(s)${skipped ? `, skipped ${skipped} busy` : ""}.`,
      );
      await fetchProviders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to switch model");
    } finally {
      setSelectingKey(null);
    }
  };

  const handleThinkingToggle = async (checked: boolean) => {
    if (!data) return;
    setThinkingBusy(true);
    setError(null);
    try {
      await v2Api.providers.select({
        default_model: data.default_model,
        default_thinking: checked,
        restart_running_sessions: true,
      });
      await fetchProviders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update thinking mode");
    } finally {
      setThinkingBusy(false);
    }
  };

  const handleSetContext = async (modelKey: string, size: number) => {
    const tier = CONTEXT_TIERS.find((t) => t.value === size);
    const label = tier?.label ?? formatContext(size);
    const warning =
      size >= 1048576
        ? `\n\nNote: a 1M context window requires an Allegretto+ subscription tier on the account behind the provider key.`
        : "";
    if (
      !window.confirm(
        `Set context window of "${modelKey}" to ${label}?${warning}`,
      )
    ) {
      return;
    }
    setContextBusyKey(modelKey);
    setError(null);
    setNotice(null);
    try {
      const resp = await v2Api.providers.setModelContext(modelKey, {
        max_context_size: size,
      });
      setData(resp);
      setNotice(`Set context window of ${modelKey} to ${label}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to set context window");
    } finally {
      setContextBusyKey(null);
    }
  };

  const handleSaveMyKey = async (providerKey: string) => {
    if (!keyInput.trim()) return;
    setKeyBusy(true);
    setError(null);
    setNotice(null);
    try {
      await v2Api.users.putMeProviderKey(providerKey, keyInput.trim());
      setNotice(`Saved your personal key for ${providerKey}.`);
      setKeyEditorFor(null);
      setKeyInput("");
      await fetchMyKeys();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save key");
    } finally {
      setKeyBusy(false);
    }
  };

  const handleDeleteMyKey = async (providerKey: string) => {
    if (!window.confirm(`Remove your personal key for "${providerKey}"?`)) {
      return;
    }
    setKeyBusy(true);
    setError(null);
    setNotice(null);
    try {
      await v2Api.users.deleteMeProviderKey(providerKey);
      setNotice(`Removed your personal key for ${providerKey}.`);
      await fetchMyKeys();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove key");
    } finally {
      setKeyBusy(false);
    }
  };

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setDialogError(null);
    setDialogOpen(true);
  };

  const openEdit = (provider: ProviderInfo) => {
    setEditing(provider);
    setForm({
      key: provider.key,
      type: provider.type,
      base_url: provider.base_url,
      api_key: "",
      rows: specsToRows(provider.models),
    });
    setDialogError(null);
    setDialogOpen(true);
  };

  const handleFetchModels = async () => {
    if (!form.base_url.trim()) {
      setDialogError("Base URL is required to fetch models");
      return;
    }
    setFetchingModels(true);
    setDialogError(null);
    try {
      const resp = await v2Api.providers.fetchModels({
        base_url: form.base_url.trim(),
        type: form.type,
        ...(form.api_key.trim()
          ? { api_key: form.api_key.trim() }
          : editing
            ? { provider_key: editing.key }
            : {}),
      });
      setForm((f) => ({ ...f, rows: specsToRows(resp.models) }));
    } catch (err) {
      setDialogError(err instanceof Error ? err.message : "Failed to fetch models");
    } finally {
      setFetchingModels(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setDialogError(null);
    try {
      const payload = {
        key: form.key.trim(),
        type: form.type,
        base_url: form.base_url.trim(),
        api_key: form.api_key.trim() || null,
        models: form.rows ? rowsToSpecs(form.rows) : null,
      };
      const resp = editing
        ? await v2Api.providers.update(editing.key, payload)
        : await v2Api.providers.create(payload);
      setData(resp);
      setDialogOpen(false);
    } catch (err) {
      setDialogError(err instanceof Error ? err.message : "Failed to save provider");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (provider: ProviderInfo) => {
    if (
      !window.confirm(
        `Delete provider "${provider.key}" and its ${provider.models.length} model(s)?`,
      )
    ) {
      return;
    }
    setError(null);
    setNotice(null);
    try {
      const resp = await v2Api.providers.delete(provider.key);
      setData(resp);
      setNotice(`Deleted provider ${provider.key}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete provider");
    }
  };

  const setRow = (idx: number, patch: Partial<ModelRow>) => {
    setForm((f) => ({
      ...f,
      rows: f.rows?.map((r, i) => (i === idx ? { ...r, ...patch } : r)) ?? null,
    }));
  };

  const hasPersonalKey = (providerKey: string) =>
    myKeys.some((k) => k.provider_key === providerKey && k.has_api_key);

  const keySourceBadge = (provider: ProviderInfo) => {
    if (hasPersonalKey(provider.key)) {
      return <Badge variant="secondary">Personal key</Badge>;
    }
    if (provider.has_api_key) {
      return <Badge variant="outline">Shared/team key</Badge>;
    }
    return <Badge variant="destructive">Not configured</Badge>;
  };

  return (
    <Layout>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Providers</h1>
          <p className="text-muted-foreground">
            {isAdmin
              ? "Manage LLM providers and switch the active model"
              : "View LLM providers and manage your personal API keys"}
          </p>
        </div>
        {isAdmin && (
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" />
            Add Provider
          </Button>
        )}
      </div>

      {!isAdmin && (
        <Alert className="mb-4">
          <AlertDescription>
            Shared providers are managed by administrators. You can set a
            personal API key for any provider below — it takes precedence over
            the shared key for your own sessions.
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {notice && (
        <Alert className="mb-4">
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      )}

      {data && (
        <div className="mb-6 flex items-center gap-3 text-sm">
          <span className="text-muted-foreground">Default model:</span>
          <Badge variant="secondary">{data.default_model}</Badge>
          <span className="text-muted-foreground ml-4">Thinking:</span>
          {isAdmin ? (
            <Switch
              checked={data.default_thinking}
              disabled={thinkingBusy}
              onCheckedChange={handleThinkingToggle}
            />
          ) : (
            <Badge variant="outline">{data.default_thinking ? "on" : "off"}</Badge>
          )}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-4">
          {data?.providers.map((provider) => (
            <Card key={provider.key}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-lg">{provider.key}</CardTitle>
                    <Badge variant="outline">{provider.type}</Badge>
                    {keySourceBadge(provider)}
                  </div>
                  {isAdmin && (
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(provider)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(provider)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  )}
                </div>
                <CardDescription className="font-mono text-xs">
                  {provider.base_url}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {provider.models.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No models configured.</p>
                ) : (
                  <div className="space-y-2">
                    {provider.models.map((spec, idx) => {
                      const modelKey = provider.model_keys[idx] ?? spec.model;
                      const isActive = modelKey === data?.default_model;
                      return (
                        <div
                          key={modelKey}
                          className="flex items-center justify-between rounded-md border px-3 py-2"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="font-mono text-sm truncate">
                              {spec.display_name || modelKey}
                            </span>
                            <Badge variant="outline" className="shrink-0">
                              {formatContext(spec.max_context_size)}
                            </Badge>
                            {spec.capabilities?.includes("thinking") && (
                              <Badge variant="secondary" className="shrink-0">
                                thinking
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            {isAdmin && (
                              <div className="flex items-center gap-1">
                                {contextBusyKey === modelKey ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  CONTEXT_TIERS.map((tier) => (
                                    <Button
                                      key={tier.value}
                                      variant={
                                        spec.max_context_size === tier.value
                                          ? "secondary"
                                          : "ghost"
                                      }
                                      size="sm"
                                      className="h-7 px-2 text-xs"
                                      disabled={
                                        contextBusyKey !== null ||
                                        spec.max_context_size === tier.value
                                      }
                                      onClick={() =>
                                        handleSetContext(modelKey, tier.value)
                                      }
                                    >
                                      {tier.label}
                                    </Button>
                                  ))
                                )}
                              </div>
                            )}
                            {isAdmin &&
                              (isActive ? (
                                <Badge className="shrink-0">
                                  <Check className="mr-1 h-3 w-3" />
                                  Active
                                </Badge>
                              ) : (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="shrink-0"
                                  disabled={selectingKey !== null}
                                  onClick={() => handleSelect(modelKey)}
                                >
                                  {selectingKey === modelKey ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                  ) : (
                                    "Use"
                                  )}
                                </Button>
                              ))}
                            {!isAdmin && isActive && (
                              <Badge className="shrink-0">
                                <Check className="mr-1 h-3 w-3" />
                                Active
                              </Badge>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Personal key */}
                <div className="rounded-md border border-dashed px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-sm">
                      <KeyRound className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">My key</span>
                      {hasPersonalKey(provider.key) ? (
                        <Badge variant="secondary">set</Badge>
                      ) : (
                        <span className="text-muted-foreground text-xs">
                          not set — falls back to shared/team key
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {keyEditorFor !== provider.key && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setKeyEditorFor(provider.key);
                            setKeyInput("");
                          }}
                        >
                          {hasPersonalKey(provider.key) ? "Replace" : "Set key"}
                        </Button>
                      )}
                      {hasPersonalKey(provider.key) && (
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={keyBusy}
                          onClick={() => handleDeleteMyKey(provider.key)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      )}
                    </div>
                  </div>
                  {keyEditorFor === provider.key && (
                    <div className="mt-2 flex items-center gap-2">
                      <Input
                        type="password"
                        placeholder="sk-..."
                        value={keyInput}
                        onChange={(e) => setKeyInput(e.target.value)}
                      />
                      <Button
                        size="sm"
                        disabled={keyBusy || !keyInput.trim()}
                        onClick={() => handleSaveMyKey(provider.key)}
                      >
                        {keyBusy && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}
                        Save
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setKeyEditorFor(null);
                          setKeyInput("");
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Usage */}
      <Collapsible open={usageOpen} onOpenChange={setUsageOpen} className="mt-6">
        <Card>
          <CollapsibleTrigger asChild>
            <CardHeader className="cursor-pointer pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Usage</CardTitle>
                <ChevronDown
                  className={`h-4 w-4 text-muted-foreground transition-transform ${usageOpen ? "rotate-180" : ""}`}
                />
              </div>
              <CardDescription>
                Token usage per provider and key source.
              </CardDescription>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent>
              {usage.length === 0 ? (
                <p className="text-sm text-muted-foreground">No usage recorded yet.</p>
              ) : (
                <div className="space-y-2">
                  {usage.map((row) => (
                    <div
                      key={`${row.provider_key}:${row.source}`}
                      className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="font-mono truncate">{row.provider_key}</span>
                        <Badge variant="outline" className="shrink-0">
                          {row.source}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 text-muted-foreground shrink-0">
                        <span>
                          {formatTokens(row.input_tokens)} in /{" "}
                          {formatTokens(row.output_tokens)} out
                        </span>
                        {row.remaining_tokens !== null && (
                          <Badge variant="secondary" className="shrink-0">
                            {formatTokens(row.remaining_tokens)} remaining
                            {row.quota_tokens !== null &&
                              ` of ${formatTokens(row.quota_tokens)}`}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editing ? `Edit ${editing.key}` : "Add provider"}</DialogTitle>
            <DialogDescription>
              {editing
                ? "Leave the API key blank to keep the stored key."
                : "Models are fetched from {base_url}/models when none are listed."}
            </DialogDescription>
          </DialogHeader>
          {dialogError && (
            <Alert variant="destructive">
              <AlertDescription>{dialogError}</AlertDescription>
            </Alert>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Key</label>
                <Input
                  value={form.key}
                  disabled={!!editing}
                  placeholder="tokendance"
                  onChange={(e) => setForm((f) => ({ ...f, key: e.target.value }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Type</label>
                <Select
                  value={form.type}
                  onValueChange={(v) => setForm((f) => ({ ...f, type: v }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PROVIDER_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Base URL</label>
              <Input
                value={form.base_url}
                placeholder="https://example.com/v1"
                onChange={(e) => setForm((f) => ({ ...f, base_url: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">API Key</label>
              <Input
                type="password"
                value={form.api_key}
                placeholder={editing ? "(unchanged)" : "sk-..."}
                onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Models</label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={fetchingModels}
                    onClick={handleFetchModels}
                  >
                    {fetchingModels ? (
                      <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <RefreshCw className="mr-1 h-3.5 w-3.5" />
                    )}
                    Fetch models
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setForm((f) => ({
                        ...f,
                        rows: [
                          ...(f.rows ?? []),
                          {
                            model: "",
                            max_context_size: "262144",
                            capabilities: "",
                            display_name: "",
                          },
                        ],
                      }))
                    }
                  >
                    <Plus className="mr-1 h-3.5 w-3.5" />
                    Add model
                  </Button>
                </div>
              </div>
              {form.rows === null ? (
                <p className="text-sm text-muted-foreground">
                  No explicit models — they will be fetched automatically on save.
                </p>
              ) : (
                <div className="space-y-2">
                  {form.rows.map((row, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <Input
                        className="flex-[2]"
                        placeholder="model id"
                        value={row.model}
                        onChange={(e) => setRow(idx, { model: e.target.value })}
                      />
                      <Input
                        className="w-24"
                        placeholder="context"
                        value={row.max_context_size}
                        onChange={(e) =>
                          setRow(idx, { max_context_size: e.target.value })
                        }
                      />
                      <Input
                        className="flex-[2]"
                        placeholder="capabilities, comma-sep"
                        value={row.capabilities}
                        onChange={(e) => setRow(idx, { capabilities: e.target.value })}
                      />
                      <Input
                        className="flex-[2]"
                        placeholder="display name"
                        value={row.display_name}
                        onChange={(e) => setRow(idx, { display_name: e.target.value })}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setForm((f) => ({
                            ...f,
                            rows: f.rows?.filter((_, i) => i !== idx) ?? null,
                          }))
                        }
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button type="submit" disabled={submitting}>
                {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {editing ? "Save changes" : "Create provider"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
