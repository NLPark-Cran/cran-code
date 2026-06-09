import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import TeamSelector from "./TeamSelector";
import { useAuthStore } from "@/stores/auth";
import { Settings } from "lucide-react";
import SettingsDialog from "./SettingsDialog";

interface LayoutProps {
  children: React.ReactNode;
  breadcrumbs?: React.ReactNode;
}

export default function Layout({ children, breadcrumbs }: LayoutProps) {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <img
              src="/logo.png"
              alt="Cran"
              className="size-6 cursor-pointer"
              onClick={() => navigate("/dashboard")}
            />
            <span className="font-semibold">Cran Code</span>
            <span className="text-muted-foreground">/</span>
            <TeamSelector />
            {breadcrumbs && (
              <>
                <span className="text-muted-foreground">/</span>
                {breadcrumbs}
              </>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground hidden sm:inline">
              {user?.display_name || user?.username || user?.email}
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setSettingsOpen(true)}
              title="Settings"
            >
              <Settings className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={() => navigate("/")}>
              Chat
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </div>
  );
}
