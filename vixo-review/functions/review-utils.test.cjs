const test = require("node:test");
const assert = require("node:assert/strict");
const { randomUUID } = require("node:crypto");
const { isValidLaunchId } = require("./review-utils.cjs");

test("accepts fresh UUIDs from iOS launch", () => {
  assert.equal(isValidLaunchId(randomUUID()), true);
  assert.equal(isValidLaunchId("550E8400-E29B-41D4-A716-446655440000"), true);
});
test("rejects hardware IDs, missing IDs and injection strings", () => {
  for (const input of [null, 0, "", "00000000-0000-0000-0000-000000000000", "abc", "../sessions", "x".repeat(400)]) {
    assert.equal(isValidLaunchId(input), false);
  }
});
