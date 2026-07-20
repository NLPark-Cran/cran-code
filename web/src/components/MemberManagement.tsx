import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Plus, UserMinus, Loader2, Search } from "lucide-react";
import { v2Api, type TeamMemberRes, type ProjectMemberRes, type UserProfile } from "@/lib/api/v2";
import { useAuthStore } from "@/stores/auth";
import { roleKey } from "@/i18n";

type Member = TeamMemberRes | ProjectMemberRes;

interface MemberManagementProps {
  members: Member[];
  resourceId: string; // teamId or projectId
  resourceType: "team" | "project";
  canManage: boolean;
  onChange: () => void;
}

export default function MemberManagement({
  members,
  resourceId,
  resourceType,
  canManage,
  onChange,
}: MemberManagementProps) {
  const { user } = useAuthStore();
  const { t } = useTranslation();
  const [addOpen, setAddOpen] = useState(false);
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<UserProfile[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserProfile | null>(null);
  const [selectedRole, setSelectedRole] = useState("member");
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const isSelf = (m: Member) => m.user_id === user?.id;

  const doSearch = useCallback(async () => {
    if (!searchQ.trim()) return;
    setSearchLoading(true);
    try {
      const results = await v2Api.users.search(searchQ.trim());
      // Exclude already members
      const memberIds = new Set(members.map((m) => m.user_id));
      setSearchResults(results.filter((u) => !memberIds.has(u.id)));
    } catch (e) {
      setActionError(e instanceof Error ? e.message : t("common:searchFailed"));
    } finally {
      setSearchLoading(false);
    }
  }, [searchQ, members, t]);

  const handleAdd = async () => {
    if (!selectedUser) return;
    setActionLoading(true);
    setActionError(null);
    try {
      if (resourceType === "team") {
        await v2Api.teams.addMember(resourceId, selectedUser.id, selectedRole);
      } else {
        await v2Api.projects.addMember(resourceId, selectedUser.id, selectedRole);
      }
      setAddOpen(false);
      setSelectedUser(null);
      setSearchQ("");
      setSearchResults([]);
      onChange();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : t("common:addMemberFailed"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleRoleChange = async (memberId: string, newRole: string) => {
    setActionLoading(true);
    try {
      if (resourceType === "team") {
        await v2Api.teams.updateMember(resourceId, memberId, newRole);
      } else {
        await v2Api.projects.updateMember(resourceId, memberId, newRole);
      }
      onChange();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : t("common:updateRoleFailed"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleRemove = async (memberId: string) => {
    if (!confirm(t("common:confirmRemoveMember"))) return;
    setActionLoading(true);
    try {
      if (resourceType === "team") {
        await v2Api.teams.removeMember(resourceId, memberId);
      } else {
        await v2Api.projects.removeMember(resourceId, memberId);
      }
      onChange();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : t("common:removeMemberFailed"));
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold">{t("common:members")}</h3>
        {canManage && (
          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger asChild>
              <Button size="sm" variant="outline">
                <Plus className="mr-1 h-3.5 w-3.5" />
                {t("common:add")}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t("common:addMember")}</DialogTitle>
                <DialogDescription>{t("common:addMemberDesc")}</DialogDescription>
              </DialogHeader>
              {actionError && (
                <Alert variant="destructive">
                  <AlertDescription>{actionError}</AlertDescription>
                </Alert>
              )}
              <div className="flex gap-2">
                <Input
                  placeholder={t("common:searchUsersPlaceholder")}
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && doSearch()}
                />
                <Button size="icon" variant="outline" onClick={doSearch} disabled={searchLoading}>
                  {searchLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                </Button>
              </div>
              <div className="max-h-40 space-y-1 overflow-auto">
                {searchResults.map((u) => (
                  <button
                    key={u.id}
                    onClick={() => setSelectedUser(u)}
                    className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent ${
                      selectedUser?.id === u.id ? "bg-accent" : ""
                    }`}
                  >
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-secondary text-xs font-medium">
                      {(u.display_name || u.username).charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="font-medium">{u.display_name || u.username}</p>
                      <p className="text-xs text-muted-foreground">{u.username}</p>
                    </div>
                  </button>
                ))}
                {searchResults.length === 0 && !searchLoading && searchQ && (
                  <p className="text-sm text-muted-foreground">{t("common:noUsersFound")}</p>
                )}
              </div>
              {selectedUser && (
                <div className="flex items-center gap-2">
                  <Select value={selectedRole} onValueChange={setSelectedRole}>
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="member">{t("common:roleMember")}</SelectItem>
                      <SelectItem value="admin">{t("common:roleAdmin")}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
              <DialogFooter>
                <Button onClick={handleAdd} disabled={!selectedUser || actionLoading}>
                  {actionLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {t("common:addMember")}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {actionError && !addOpen && (
        <Alert variant="destructive">
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-2">
        {members.map((m) => (
          <div key={m.id} className="flex items-center justify-between rounded-md border px-3 py-2">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-xs font-medium">
                {(m.display_name || m.username).charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-medium">
                  {m.display_name || m.username}
                  {isSelf(m) && (
                    <span className="ml-1 text-xs text-muted-foreground">{t("common:you")}</span>
                  )}
                </p>
                <p className="text-xs text-muted-foreground">{m.username}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {canManage && !isSelf(m) ? (
                <>
                  <Select
                    value={m.role}
                    onValueChange={(v) => handleRoleChange(m.id, v)}
                    disabled={actionLoading}
                  >
                    <SelectTrigger className="h-7 w-24 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="member">{t("common:roleMember")}</SelectItem>
                      <SelectItem value="admin">{t("common:roleAdmin")}</SelectItem>
                      <SelectItem value="owner">{t("common:roleOwner")}</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7 text-destructive"
                    onClick={() => handleRemove(m.id)}
                    disabled={actionLoading}
                  >
                    <UserMinus className="h-3.5 w-3.5" />
                  </Button>
                </>
              ) : (
                <Badge variant="secondary" className="text-xs">
                  {t(roleKey(m.role))}
                </Badge>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
