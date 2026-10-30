"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { randomUUID } = require("node:crypto");
const {
  validApproval, approvedUid, registerVirtualDevice,
} = require("./review-policy.cjs");

const now = Date.UTC(2026, 9, 30);
function user(overrides = {}) {
  return { disabled: false, customClaims: {
    vixo_app_review: true, vixo_demo_premium: true,
  }, ...overrides };
}
function grant(overrides = {}) {
  return { active: true, premium: true,
    expiresAt: new Date(now + 86400000), ...overrides };
}
function mocks(u = user(), g = grant()) {
  const writes = [];
  return {
    writes,
    getUser: async uid => { assert.equal(uid, "review-uid"); return u; },
    getGrant: async uid => { assert.equal(uid, "review-uid"); return g; },
    now: () => now,
    putLaunch: async (...args) => { writes.push(args); },
  };
}

test("requires BOTH trusted custom claims and active grant", () => {
  assert.equal(validApproval(user(), grant(), now), true);
  assert.equal(validApproval(user(), null, now), false);
  assert.equal(validApproval(null, grant(), now), false);
  assert.equal(validApproval(user({ disabled: true }), grant(), now), false);
  assert.equal(validApproval(user({ customClaims: {} }), grant(), now), false);
  assert.equal(validApproval(user(), grant({ active: false }), now), false);
  assert.equal(validApproval(user(), grant({ premium: false }), now), false);
  assert.equal(validApproval(user(), grant({ expiresAt: null }), now), false);
  assert.equal(validApproval(user(), grant({ expiresAt: new Date(now - 1) }), now), false);
  assert.equal(validApproval(user(), grant({ expiresAt: { toMillis: () => now + 1000 } }), now), true);
});
test("never approves unauthenticated UID", async () => {
  assert.equal(await approvedUid(null, { getUser: () => { throw Error("called"); } }), false);
});
test("issues a fresh virtual review-device record only to approved account", async () => {
  const services = mocks();
  const first = randomUUID();
  const second = randomUUID();
  const a = await registerVirtualDevice("review-uid", first, services);
  const b = await registerVirtualDevice("review-uid", second, services);
  assert.deepEqual(services.writes, [["review-uid", first], ["review-uid", second]]);
  assert.equal(a.virtualDeviceId, first);
  assert.equal(b.virtualDeviceId, second);
  assert.notEqual(a.virtualDeviceId, b.virtualDeviceId);
  assert.equal(a.virtualDeviceType, "app_review_process");
});
test("does not register a virtual device for disabled or expired reviewer", async () => {
  for (const g of [grant({ active: false }), grant({ expiresAt: new Date(now - 1000) })]) {
    const services = mocks(user(), g);
    const r = await registerVirtualDevice("review-uid", randomUUID(), services);
    assert.equal(r.registered, false);
    assert.equal(services.writes.length, 0);
  }
});
test("rejects malformed device/session IDs", async () => {
  const services = mocks();
  await assert.rejects(registerVirtualDevice("review-uid", "../fraud", services),
    { code: "invalid-argument" });
  assert.equal(services.writes.length, 0);
});
