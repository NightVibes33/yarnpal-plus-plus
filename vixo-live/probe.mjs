// Production read-only connectivity/auth challenge probe.
// Sends ONLY unauthenticated HTTPS GET requests to a fixed allowlist.
// Does not attempt login, generate accounts, send credit grants or log response bodies.
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export const PROBES = Object.freeze([
  "https://api.vixo.one/",
  "https://api.vixo.one/api/rest/user/points/info",
  "https://sg-user.vixo.one/",
  "https://sg-pay.vixo.one/"
]);

export async function runProbes(transport = fetch) {
  const results = [];
  for (const url of PROBES) {
    try {
      const start = Date.now();
      const response = await transport(url, {
        method: "GET",
        redirect: "manual",
        credentials: "omit",
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
        headers: {
          Accept: "application/json",
          "User-Agent": "VIXO-ReadOnly-QA-Probe/1.0"
        }
      });
      results.push({
        url,
        method: "GET",
        status: response.status,
        contentType: response.headers.get("content-type")?.split(";")[0] || null,
        elapsedMs: Date.now() - start,
        authVerified: false,
        writeAttempted: false
      });
      // Do not read or log the body. It may contain user data.
      await response.body?.cancel?.().catch(() => {});
    } catch (error) {
      results.push({
        url,
        method: "GET",
        networkError: error.name || "NetworkError",
        authVerified: false,
        writeAttempted: false
      });
    }
  }
  return {
    source: "compiled_vixo_2.2.2_strings",
    testType: "unauthenticated_read_only",
    results,
    productionCreditsChanged: false,
    caveat: "A reachable host or 200 response is not evidence of authenticated credit access."
  };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const result = await runProbes();
  if (process.argv[2] === "--json-file") {
    const file = process.argv[3];
    if (!file) throw new Error("Missing output file");
    writeFileSync(file, JSON.stringify(result, null, 2) + "\n");
  }
  console.log(JSON.stringify(result, null, 2));
}
