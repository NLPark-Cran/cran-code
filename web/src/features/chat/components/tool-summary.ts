import type { TFunction } from "i18next";

const MAX_SUMMARY_LEN = 80;

const truncate = (value: string, max = MAX_SUMMARY_LEN): string =>
  value.length > max ? `${value.slice(0, max)}…` : value;

const str = (value: unknown): string | null =>
  typeof value === "string" && value.trim().length > 0 ? value.trim() : null;

const safeStringify = (value: unknown): string => {
  try {
    return JSON.stringify(value) ?? "";
  } catch {
    return String(value);
  }
};

type SummaryFn = (input: Record<string, unknown>, t: TFunction) => string | null;

const pathSummary: SummaryFn = (input) => {
  const path = str(input.path);
  return path ? truncate(path) : null;
};

/** Read/Write/StrReplaceFile: file path (+ line count when content is known) */
const pathWithLinesSummary: SummaryFn = (input, t) => {
  const path = str(input.path);
  if (!path) return null;
  const content = str(input.content);
  if (!content) return truncate(path);
  const lines = content.split("\n").length;
  return `${truncate(path)} · ${t("chat:linesCount", { count: lines })}`;
};

const patternSummary: SummaryFn = (input) => {
  const pattern = str(input.pattern);
  return pattern ? truncate(pattern) : null;
};

const TOOL_SUMMARIES: Record<string, SummaryFn> = {
  ReadFile: pathSummary,
  ReadMediaFile: pathSummary,
  WriteFile: pathWithLinesSummary,
  StrReplaceFile: pathWithLinesSummary,
  Shell: (input) => {
    const command = str(input.command);
    return command ? truncate(command) : null;
  },
  Grep: patternSummary,
  Glob: patternSummary,
  SearchWeb: (input) => {
    const query = str(input.query);
    return query ? truncate(query) : null;
  },
  Task: (input) => {
    const parts = [str(input.description), str(input.subagent_type)].filter(
      (part): part is string => Boolean(part),
    );
    return parts.length > 0 ? truncate(parts.join(" · ")) : null;
  },
};

/** Legacy / display-name aliases → registry keys */
const NAME_ALIASES: Record<string, string> = {
  Read: "ReadFile",
  Write: "WriteFile",
  Edit: "StrReplaceFile",
  Bash: "Shell",
  WebSearch: "SearchWeb",
  Agent: "Task",
};

/**
 * One-line summary for a collapsed tool card, e.g. the file path for
 * Read/Write, the command line for Shell, the query for SearchWeb.
 * Falls back to the first 80 chars of the serialized arguments.
 */
export function getToolSummary(
  title: string | undefined,
  input: unknown,
  t: TFunction,
): string | null {
  const rawName = (title ?? "").split(":")[0].trim();
  const registryName = TOOL_SUMMARIES[rawName] ? rawName : NAME_ALIASES[rawName];
  const summaryFn = registryName ? TOOL_SUMMARIES[registryName] : undefined;
  if (summaryFn && input && typeof input === "object") {
    const summary = summaryFn(input as Record<string, unknown>, t);
    if (summary) return summary;
  }
  if (input == null) return null;
  const text = typeof input === "string" ? input : safeStringify(input);
  return text ? truncate(text) : null;
}
