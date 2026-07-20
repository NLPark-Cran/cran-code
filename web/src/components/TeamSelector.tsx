import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronsUpDown, Plus } from "lucide-react";
import { v2Api, type TeamRes } from "@/lib/api/v2";
import { useTeamStore } from "@/stores/team";

export default function TeamSelector() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { teamId: urlTeamId } = useParams<{ teamId: string }>();
  const { selectedTeamId, setSelectedTeamId } = useTeamStore();
  const [teams, setTeams] = useState<TeamRes[]>([]);

  useEffect(() => {
    v2Api.teams.list().then(setTeams).catch(() => {});
  }, []);

  // Sync with URL param when on team page
  useEffect(() => {
    if (urlTeamId) {
      setSelectedTeamId(urlTeamId);
    }
  }, [urlTeamId, setSelectedTeamId]);

  const activeTeamId = selectedTeamId;
  const activeTeam = teams.find((t) => t.id === activeTeamId);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="h-8 gap-1 px-2">
          <span className="max-w-[140px] truncate text-sm">
            {activeTeam ? activeTeam.name : t("nav:selectTeam")}
          </span>
          <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        {teams.map((t) => (
          <DropdownMenuItem
            key={t.id}
            onClick={() => {
              setSelectedTeamId(t.id);
              navigate(`/team/${t.id}`);
            }}
            className={t.id === activeTeamId ? "bg-accent" : ""}
          >
            <span className="truncate">{t.name}</span>
          </DropdownMenuItem>
        ))}
        {teams.length === 0 && (
          <DropdownMenuItem disabled>{t("nav:noTeams")}</DropdownMenuItem>
        )}
        <DropdownMenuItem onClick={() => navigate("/dashboard")}>
          <Plus className="mr-2 h-4 w-4" />
          {t("nav:newTeam")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
