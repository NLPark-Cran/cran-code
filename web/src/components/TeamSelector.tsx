import { useState, useEffect } from "react";
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

export default function TeamSelector() {
  const navigate = useNavigate();
  const { teamId } = useParams<{ teamId: string }>();
  const [teams, setTeams] = useState<TeamRes[]>([]);
  const [selected, setSelected] = useState<TeamRes | null>(null);

  useEffect(() => {
    v2Api.teams.list().then(setTeams).catch(() => {});
  }, []);

  useEffect(() => {
    if (teamId && teams.length > 0) {
      const t = teams.find((x) => x.id === teamId);
      if (t) setSelected(t);
    }
  }, [teamId, teams]);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="h-8 gap-1 px-2">
          <span className="max-w-[140px] truncate text-sm">
            {selected ? selected.name : "Select team"}
          </span>
          <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        {teams.map((t) => (
          <DropdownMenuItem
            key={t.id}
            onClick={() => navigate(`/team/${t.id}`)}
            className={t.id === selected?.id ? "bg-accent" : ""}
          >
            <span className="truncate">{t.name}</span>
          </DropdownMenuItem>
        ))}
        {teams.length === 0 && (
          <DropdownMenuItem disabled>No teams</DropdownMenuItem>
        )}
        <DropdownMenuItem onClick={() => navigate("/dashboard")}>
          <Plus className="mr-2 h-4 w-4" />
          New team
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
