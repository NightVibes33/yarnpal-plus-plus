"use strict";
const fs=require("node:fs"), assert=require("node:assert/strict");
const [a,b,c]=process.argv.slice(2);
const first=JSON.parse(fs.readFileSync(a)),second=JSON.parse(fs.readFileSync(b)),ledger=JSON.parse(fs.readFileSync(c));
for(const [i,run] of [first,second].entries()){
  assert.ok(!run.error,"iOS run "+(i+1)+" failed: "+run.error);
  assert.equal(run.qaOnly,true);
  assert.equal(run.accounts.length,2);
  assert.deepEqual(run.accounts.map(x=>x.uid),["qa-one","qa-two"]);
  for(const account of run.accounts){
    assert.equal(account.registered,true);
    assert.equal(account.session,run.launchId);
    assert.equal(account.grant,9999);
    assert.equal(account.before,9999);
    assert.equal(account.after,9899);
  }
}
assert.notEqual(first.launchId,second.launchId,"Process-scoped ID should rotate");
assert.equal(ledger.launches.length,4,"Two stable accounts x two unique launches");
assert.equal(ledger.wallets["qa-one"],9899);
assert.equal(ledger.wallets["qa-two"],9899);
console.log("PASS: simulator launched twice; both users logged in, granted 9999, spent 100; per-process UUID changed.");
