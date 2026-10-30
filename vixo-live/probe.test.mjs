import { test } from "node:test";
import assert from "node:assert/strict";
import { runProbes, PROBES } from "./probe.mjs";

test("only expected HTTPS allowlisted production services and known read endpoint", () => {
  assert.deepEqual(PROBES, [
    "https://api.vixo.one/",
    "https://api.vixo.one/api/rest/user/points/info",
    "https://sg-user.vixo.one/",
    "https://sg-pay.vixo.one/"
  ]);
  for (const value of PROBES) {
    assert.equal(new URL(value).protocol, "https:");
  }
});
test("all calls are unauthenticated, read-only and no response body is inspected", async () => {
  let seen = 0, bodyRead = false;
  const transport = async (url, options) => {
    assert.ok(PROBES.includes(url));
    assert.equal(options.method, "GET");
    assert.equal(options.redirect, "manual");
    assert.equal(options.credentials, "omit");
    assert.ok(!("Authorization" in options.headers));
    seen++;
    return {
      status: 401,
      headers: new Headers({ "content-type": "application/json" }),
      body: { cancel: async () => {} },
      text: async () => { bodyRead = true; throw Error("Sensitive response must not be read"); },
      json: async () => { bodyRead = true; throw Error("Sensitive response must not be read"); }
    };
  };
  const report = await runProbes(transport);
  assert.equal(seen, PROBES.length);
  assert.equal(bodyRead, false);
  assert.ok(report.results.every(x => x.status === 401 && x.writeAttempted === false));
  assert.equal(report.productionCreditsChanged, false);
});
test("network failures are isolated to their target host", async () => {
  const report = await runProbes(async url => {
    if (url === PROBES[0]) throw Object.assign(new Error("offline"), { name: "TypeError" });
    return { status: 403, headers: new Headers(), body: null };
  });
  assert.equal(report.results.length, PROBES.length);
  assert.equal(report.results[0].networkError, "TypeError");
  assert.equal(report.results[1].status, 403);
});
