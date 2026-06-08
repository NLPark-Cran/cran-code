import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Plus, Users, ArrowRight, Loader2, LayoutDashboard } from "lucide-react";
import { v2Api, type TeamRes } from "@/lib/api/v2";
import { useAuthStore } from "@/stores/auth";

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [teams, setTeams] = useState<TeamRes[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createSlug, setCreateSlug] = useState("");
  const [createDesc, setCreateDesc] = useState("");
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchTeams = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await v2Api.teams.list();
      setTeams(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load teams");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeams();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createName.trim() || !createSlug.trim()) return;
    setCreateLoading(true);
    setCreateError(null);
    try {
      const team = await v2Api.teams.create({
        name: createName.trim(),
        slug: createSlug.trim().toLowerCase().replace(/\s+/g, "-"),
        description: createDesc.trim() || undefined,
      });
      setCreateOpen(false);
      setCreateName("");
      setCreateSlug("");
      setCreateDesc("");
      navigate(`/team/${team.id}`);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create team");
    } finally {
      setCreateLoading(false);
    }
  };

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="Cran" className="size-6" />
            <span className="font-semibold">Cran Code</span>
            <span className="text-muted-foreground">/</span>
            <span className="text-sm text-muted-foreground">Dashboard</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground hidden sm:inline">
              {user?.display_name || user?.username || user?.email}
            </span>
            <Button variant="outline" size="sm" onClick={() => navigate("/")}>
              Chat
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Teams</h1>
            <p className="text-muted-foreground">
              Manage your teams and projects
            </p>
          </div>
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                New Team
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create a new team</DialogTitle>
                <DialogDescription>
                  Teams are shared workspaces for projects and collaboration.
                </DialogDescription>
              </DialogHeader>
              {createError && (
                <Alert variant="destructive">
                  <AlertDescription>{createError}</AlertDescription>
                </Alert>
              )}
              <form onSubmit={handleCreate} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Team Name</label>
                  <Input
                    placeholder="My Team"
                    value={createName}
                    onChange={(e) => {
                      setCreateName(e.target.value);
                      if (!createSlug || createSlug === generateSlug(createName)) {
                        setCreateSlug(generateSlug(e.target.value));
                      }
                    }}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Slug</label>
                  <Input
                    placeholder="my-team"
                    value={createSlug}
                    onChange={(e) => setCreateSlug(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Description</label>
                  <Textarea
                    placeholder="What is this team about?"
                    value={createDesc}
                    onChange={(e) => setCreateDesc(e.target.value)}
                  />
                </div>
                <DialogFooter>
                  <Button type="submit" disabled={createLoading}>
                    {createLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Create Team
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : teams.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-16">
              <Users className="mb-4 h-12 w-12 text-muted-foreground" />
              <p className="text-lg font-medium">No teams yet</p>
              <p className="text-muted-foreground">
                Create your first team to start collaborating
              </p>
              <Button className="mt-4" onClick={() => setCreateOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Team
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {teams.map((team) => (
              <Card
                key={team.id}
                className="cursor-pointer transition-shadow hover:shadow-md"
                onClick={() => navigate(`/team/${team.id}`)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-lg">{team.name}</CardTitle>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <CardDescription className="line-clamp-2">
                    {team.description || "No description"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Users className="h-4 w-4" />
                    <span>{team.members.length} members</span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {team.members.slice(0, 3).map((m) => (
                      <Badge key={m.id} variant="secondary" className="text-xs">
                        {m.display_name || m.username}
                      </Badge>
                    ))}
                    {team.members.length > 3 && (
                      <Badge variant="secondary" className="text-xs">
                        +{team.members.length - 3}
                      </Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
