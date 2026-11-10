import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const frontendRoot = resolve(import.meta.dirname, "..");
const openApiSource = process.env.OPENAPI_SOURCE ?? resolve(frontendRoot, "openapi.json");
const committedSchemaPath = resolve(frontendRoot, "src/api/generated/schema.ts");
const openApiCli = resolve(frontendRoot, "node_modules/openapi-typescript/bin/cli.js");

const tempDir = mkdtempSync(join(tmpdir(), "finsignal-openapi-"));
const tempSchemaPath = join(tempDir, "schema.ts");

try {
  execFileSync(process.execPath, [openApiCli, openApiSource, "-o", tempSchemaPath], {
    cwd: frontendRoot,
    stdio: "pipe",
  });

  const normalize = (text) => text.replace(/\r\n/g, "\n");
  const committed = normalize(readFileSync(committedSchemaPath, "utf8"));
  const regenerated = normalize(readFileSync(tempSchemaPath, "utf8"));

  if (committed !== regenerated) {
    console.error(
      "Contract drift detected: src/api/generated/schema.ts does not match OpenAPI source:",
      openApiSource
    );
    process.exitCode = 1;
  } else {
    console.log("OpenAPI TypeScript contract is up to date (zero drift).");
  }
} finally {
  rmSync(tempDir, { recursive: true, force: true });
}
