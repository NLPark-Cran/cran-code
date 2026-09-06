import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { EyeIcon, EyeOffIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { redactSecrets } from "@/lib/redact";
import { CodeBlock } from "@/components/ai-elements/code-block";

type RevealButtonProps = {
  revealed: boolean;
  onToggle: () => void;
  className?: string;
};

function RevealButton({ revealed, onToggle, className }: RevealButtonProps) {
  const { t } = useTranslation();
  return (
    <button
      type="button"
      aria-label={t(revealed ? "common:hideSecret" : "common:showSecret")}
      title={t(revealed ? "common:hideSecret" : "common:showSecret")}
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
      className={cn(
        "inline-flex shrink-0 cursor-pointer items-center justify-center rounded p-0.5 text-muted-foreground/60 transition-colors hover:bg-secondary/60 hover:text-foreground",
        className,
      )}
    >
      {revealed ? <EyeOffIcon className="size-3" /> : <EyeIcon className="size-3" />}
    </button>
  );
}

/**
 * Inline text with secrets masked as `***` by default; an eye toggle reveals
 * the raw text. Renders plain text unchanged when there is nothing to mask.
 */
export function RedactedText({
  text,
  className,
}: {
  text: string;
  className?: string;
}) {
  const masked = useMemo(() => redactSecrets(text), [text]);
  const [revealed, setRevealed] = useState(false);

  if (masked === text) {
    return <span className={className}>{text}</span>;
  }
  return (
    <span className={cn("inline-flex items-baseline gap-1", className)}>
      <span className="min-w-0 break-all">{revealed ? text : masked}</span>
      <RevealButton revealed={revealed} onToggle={() => setRevealed((r) => !r)} />
    </span>
  );
}

/**
 * CodeBlock wrapper with the same masked-by-default + eye-toggle behavior
 * for multi-line content (commands, outputs, JSON blobs).
 */
export function RedactedCodeBlock({
  code,
  language,
}: {
  code: string;
  language: string;
}) {
  const masked = useMemo(() => redactSecrets(code), [code]);
  const [revealed, setRevealed] = useState(false);

  if (masked === code) {
    return <CodeBlock code={code} language={language} />;
  }
  return (
    <div className="relative">
      <CodeBlock code={revealed ? code : masked} language={language} />
      <RevealButton
        revealed={revealed}
        onToggle={() => setRevealed((r) => !r)}
        className="absolute right-1.5 top-1.5 bg-background/80"
      />
    </div>
  );
}
