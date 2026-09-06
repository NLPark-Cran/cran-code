/**
 * Secret redaction for tool-call arguments/results rendered in the UI.
 * Display-only masking: the underlying data is untouched; components offer
 * an eye-toggle to reveal the raw text on demand.
 */

const MASK = "***";

/** KEY=VALUE pairs where the value is a secret (key name preserved). */
const ENV_ASSIGNMENT_REGEX = /\b(\w*(?:TOKEN|PASSWORD|API_KEY|SECRET|PASSWD)\w*)=(\S+)/gi;

/** Well-known token prefixes. */
const TOKEN_PATTERNS: RegExp[] = [
  /github_pat_[A-Za-z0-9_]+/g,
  /ghp_[A-Za-z0-9]+/g,
  /sk-[A-Za-z0-9]{8,}/g,
  /cwk_[A-Za-z0-9]+/g,
];

const BEARER_REGEX = /Bearer\s+\S+/gi;

/** Generic long-token heuristic (JWTs, session tokens, base64 blobs…). */
const LONG_TOKEN_REGEX = /[A-Za-z0-9_-]{40,}/g;

/** 40-char lowercase hex is almost always a git SHA — do not mask it. */
const GIT_SHA_REGEX = /^[a-f0-9]{40}$/;

export function redactSecrets(text: string): string {
  if (!text) return text;
  let out = text;
  out = out.replace(ENV_ASSIGNMENT_REGEX, `$1=${MASK}`);
  out = out.replace(BEARER_REGEX, `Bearer ${MASK}`);
  for (const pattern of TOKEN_PATTERNS) {
    out = out.replace(pattern, MASK);
  }
  out = out.replace(LONG_TOKEN_REGEX, (m) => (GIT_SHA_REGEX.test(m) ? m : MASK));
  return out;
}

export function containsSecrets(text: string): boolean {
  return redactSecrets(text) !== text;
}
