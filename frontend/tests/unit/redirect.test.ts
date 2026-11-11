import { describe, expect, it } from "vitest";
import { buildLoginRedirectPath, sanitizeRedirectPath } from "../../src/lib/auth/redirect.ts";

describe("sanitizeRedirectPath & buildLoginRedirectPath (F2.3)", () => {
  it("preserves safe internal application paths including query params and hashes", () => {
    expect(sanitizeRedirectPath("/")).toBe("/");
    expect(sanitizeRedirectPath("/transactions?page=2&sort=desc")).toBe(
      "/transactions?page=2&sort=desc"
    );
    expect(sanitizeRedirectPath("/investigations/inv-42#evidence")).toBe(
      "/investigations/inv-42#evidence"
    );
    expect(sanitizeRedirectPath("/datasets?tab=imports")).toBe("/datasets?tab=imports");
  });

  it("rejects external, protocol-relative, backslash, scheme-bearing, control-char, and loop paths", () => {
    expect(sanitizeRedirectPath(undefined)).toBe("/");
    expect(sanitizeRedirectPath(null)).toBe("/");
    expect(sanitizeRedirectPath("")).toBe("/");
    expect(sanitizeRedirectPath("   ")).toBe("/");
    expect(sanitizeRedirectPath("https://evil.example/phish")).toBe("/");
    expect(sanitizeRedirectPath("http://evil.example")).toBe("/");
    expect(sanitizeRedirectPath("//evil.example/phish")).toBe("/");
    expect(sanitizeRedirectPath("/\\evil.example")).toBe("/");
    expect(sanitizeRedirectPath("javascript:alert(1)")).toBe("/");
    expect(sanitizeRedirectPath("data:text/html,<script>alert(1)</script>")).toBe("/");
    expect(sanitizeRedirectPath("/transactions\nLocation:https://evil.example")).toBe("/");
    expect(sanitizeRedirectPath("/login")).toBe("/");
    expect(sanitizeRedirectPath("/login?redirect=/transactions")).toBe("/");
    expect(sanitizeRedirectPath("/transactions?token=secret-jwt")).toBe("/");
    expect(sanitizeRedirectPath("transactions")).toBe("/");
  });

  it("builds login redirect URL cleanly without encoding root path", () => {
    expect(buildLoginRedirectPath("/")).toBe("/login");
    expect(buildLoginRedirectPath("https://evil.example")).toBe("/login");
    expect(buildLoginRedirectPath("/investigations?status=OPEN")).toBe(
      "/login?redirect=%2Finvestigations%3Fstatus%3DOPEN"
    );
  });
});
