import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";
import { v2Api, type ActivityRes } from "@/lib/api/v2";

interface ActivityStreamProps {
  projectId: string;
  refreshKey?: number;
}

const typeLabelKeys: Record<string, string> = {
  message_sent: "project:actMessage",
  file_edited: "project:actFileEdit",
  file_deleted: "project:actDelete",
  file_uploaded: "project:actUpload",
  file_downloaded: "project:actDownload",
  command_run: "project:actCommand",
  session_created: "project:actSession",
  session_forked: "project:actFork",
  commit_pushed: "project:actCommit",
  review_submitted: "project:actReview",
};

const typeColorKeys: Record<string, string> = {
  message_sent: "bg-blue-100 text-blue-800",
  file_edited: "bg-amber-100 text-amber-800",
  file_deleted: "bg-red-100 text-red-800",
  file_uploaded: "bg-emerald-100 text-emerald-800",
  file_downloaded: "bg-cyan-100 text-cyan-800",
  command_run: "bg-purple-100 text-purple-800",
  session_created: "bg-green-100 text-green-800",
  session_forked: "bg-teal-100 text-teal-800",
  commit_pushed: "bg-orange-100 text-orange-800",
  review_submitted: "bg-pink-100 text-pink-800",
};

function formatTime(iso: string, t: (key: string, opts?: { count: number }) => string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = (now.getTime() - d.getTime()) / 1000;
  if (diff < 60) return t("project:justNow");
  if (diff < 3600) return t("project:minutesAgo", { count: Math.floor(diff / 60) });
  if (diff < 86400) return t("project:hoursAgo", { count: Math.floor(diff / 3600) });
  return t("project:daysAgo", { count: Math.floor(diff / 86400) });
}

export default function ActivityStream({ projectId, refreshKey }: ActivityStreamProps) {
  const { t } = useTranslation();
  const [activities, setActivities] = useState<ActivityRes[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchActivities = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await v2Api.projects.listActivities(projectId, 50);
      setActivities(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("project:activityLoadFailed"));
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities, refreshKey]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold">{t("project:activityTitle")}</h3>
        <button
          onClick={fetchActivities}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          {t("common:refresh")}
        </button>
      </div>

      {loading ? (
        <div className="flex h-32 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : activities.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("project:activityEmpty")}</p>
      ) : (
        <div className="space-y-3">
          {activities.map((a) => (
            <div key={a.id} className="flex gap-2 text-sm">
              <Badge
                variant="secondary"
                className={`shrink-0 text-[10px] ${typeColorKeys[a.type] || ""}`}
              >
                {typeLabelKeys[a.type] ? t(typeLabelKeys[a.type]) : a.type}
              </Badge>
              <div className="min-w-0">
                <p className="truncate">
                  <span className="font-medium">
                    {a.display_name || a.username || t("project:activitySystem")}
                  </span>
                  {a.payload && (
                    <span className="text-muted-foreground"> {a.payload}</span>
                  )}
                </p>
                <p className="text-xs text-muted-foreground">{formatTime(a.created_at, t)}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
