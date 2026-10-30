"use strict";
const QA_CREDITS = 9999;

/**
 * Assign exactly 9,999 QA credits to the authenticated Firebase UID.
 * The caller (Cloud Function) must verify authentication and feature gate.
 * The supplied persist callback is authoritative for the test ledger.
 */
async function ensureQaCredits(uid, persist) {
  if (typeof uid !== "string" || uid.length === 0) {
    const error = new Error("Authentication is required");
    error.code = "unauthenticated";
    throw error;
  }
  if (typeof persist !== "function") throw new TypeError("Missing balance writer");
  await persist(uid, QA_CREDITS);
  return { credits: QA_CREDITS, source: "owner_qa_fixture" };
}
module.exports = { QA_CREDITS, ensureQaCredits };
