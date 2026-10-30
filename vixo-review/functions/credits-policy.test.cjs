"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { QA_CREDITS, ensureQaCredits } = require("./credits-policy.cjs");

test("authenticated users get exactly 9999 QA credits", async () => {
  const records = [];
  for (const uid of ["user-A", "user-B"]) {
    const reply = await ensureQaCredits(uid, async (id, amount) => records.push([id, amount]));
    assert.equal(reply.credits, 9999);
  }
  assert.equal(QA_CREDITS, 9999);
  assert.deepEqual(records, [["user-A", 9999], ["user-B", 9999]]);
});
test("repeated logins reassert the same credit balance", async () => {
  const state = {};
  const save = async (uid, credits) => { state[uid] = credits; };
  await ensureQaCredits("uid", save);
  state.uid = 150;
  await ensureQaCredits("uid", save);
  assert.equal(state.uid, 9999);
});
test("rejects missing users without writing", async () => {
  let writes = 0;
  const save = async () => { writes++; };
  for (const uid of ["", null, undefined]) {
    await assert.rejects(ensureQaCredits(uid, save), { code: "unauthenticated" });
  }
  assert.equal(writes, 0);
});
test("does not claim a grant when database persistence fails", async () => {
  await assert.rejects(ensureQaCredits("user", async () => { throw Error("unavailable"); }), /unavailable/);
});
