import { describe, expect, it } from "vitest";
import { containsSecrets, redactSecrets } from "./redact";

describe("redactSecrets", () => {
  it("masks GitHub PATs", () => {
    expect(redactSecrets("token: github_pat_11ABCDEFG0abcdefghi_zz")).toBe(
      "token: ***",
    );
  });

  it("masks ghp_ tokens", () => {
    expect(redactSecrets("ghp_a1b2c3d4e5f6")).toBe("***");
  });

  it("masks sk- API keys", () => {
    expect(redactSecrets("key = sk-abcdefgh12345678")).toBe("key = ***");
  });

  it("masks cwk_ proxy tokens", () => {
    expect(redactSecrets("Authorization: cwk_deadbeef123")).toBe(
      "Authorization: ***",
    );
  });

  it("masks Bearer headers but keeps the scheme", () => {
    expect(redactSecrets("Bearer eyJhbGciOiJ9.sig")).toBe("Bearer ***");
  });

  it("masks KEY=VALUE secrets but keeps the key name", () => {
    expect(redactSecrets("OPENAI_API_KEY=sk-topsecret99")).toBe(
      "OPENAI_API_KEY=***",
    );
    expect(redactSecrets("ROOT_PASSWORD=20070703Three#%")).toBe(
      "ROOT_PASSWORD=***",
    );
  });

  it("masks generic long tokens", () => {
    const jwt = `eyJ${"a".repeat(50)}`;
    expect(redactSecrets(jwt)).toBe("***");
  });

  it("does not mask git SHAs", () => {
    const sha = "a".repeat(39) + "1"; // 40 hex chars
    expect(redactSecrets(`commit ${sha}`)).toBe(`commit ${sha}`);
  });

  it("leaves ordinary text untouched", () => {
    const text = "ls -la /root && echo hello world";
    expect(redactSecrets(text)).toBe(text);
  });

  it("handles empty input", () => {
    expect(redactSecrets("")).toBe("");
  });
});

describe("containsSecrets", () => {
  it("detects secrets", () => {
    expect(containsSecrets("ghp_a1b2c3d4")).toBe(true);
  });

  it("returns false for clean text", () => {
    expect(containsSecrets("hello world")).toBe(false);
  });
});
