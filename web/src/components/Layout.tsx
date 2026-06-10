import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import TeamSelector from "./TeamSelector";
import { useAuthStore } from "@/stores/auth";
import { Settings, LogOut, User } from "lucide-react";
import SettingsDialog from "./SettingsDialog";

interface LayoutProps {
  children: React.ReactNode;
  breadcrumbs?: React.ReactNode;
}

export default function Layout({ children, breadcrumbs }: LayoutProps) {
  const navigate = useNavigate();
  const { user, clearAuth } = useAuthStore();
  const [settingsOpen, setSettingsOpen] = useState(false);

  const handleLogout = () => {
    clearAuth();
    navigate("/login");
  };

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
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 gap-1.5 px-2 hidden sm:flex">
                  <User className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground max-w-[120px] truncate">
                    {user?.display_name || user?.username || user?.email}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setSettingsOpen(true)}>
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive">
                  <LogOut className="mr-2 h-4 w-4" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
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
