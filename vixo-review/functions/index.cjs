"use strict";
const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { initializeApp } = require("firebase-admin/app");
const { getAuth } = require("firebase-admin/auth");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");
const { approvedUid, registerVirtualDevice } = require("./review-policy.cjs");

initializeApp();
const region = "us-central1";

function services() {
  return {
    getUser: uid => getAuth().getUser(uid),
    getGrant: async uid => {
      const snap = await getFirestore().collection("vixoReviewAccounts").doc(uid).get();
      return snap.exists ? snap.data() : null;
    },
    putLaunch: (uid, launchId) => getFirestore()
      .collection("vixoReviewSessions")
      .doc(uid)
      .collection("launches")
      .doc(launchId)
      .set({
        launchId,
        virtualDeviceId: launchId,
        type: "app_review_process",
        createdAt: FieldValue.serverTimestamp(),
      }, { merge: true }),
  };
}

// Integration is opt-in and requires Firebase Auth to be the original app's
// authority. If VIXO uses its own login stack, connect that stack to equivalent
// backend-side checks instead of invoking an unrelated Firebase identity.
exports.vixoReviewAccess = onCall({ region }, async (request) => {
  if (!request.auth) throw new HttpsError("unauthenticated", "Sign in first.");
  const approved = await approvedUid(request.auth.uid, services());
  return approved
    ? { review: true, premium: true, entitlement: "app_review_demo" }
    : { review: false, premium: false };
});

exports.vixoReviewLaunch = onCall({ region }, async (request) => {
  if (!request.auth) throw new HttpsError("unauthenticated", "Sign in first.");
  try {
    return await registerVirtualDevice(
      request.auth.uid, request.data?.launchId, services(),
    );
  } catch (e) {
    if (e.code === "invalid-argument") {
      throw new HttpsError("invalid-argument", e.message);
    }
    throw e;
  }
});

const { ensureQaCredits } = require("./credits-policy.cjs");

// QA-only Firebase credit fixture. This does NOT change VIXO's own payment
// service until its original backend explicitly reads this credit ledger.
// Disabled unless the owner enables VIXO_QA_CREDITS_ENABLED=true on the
// dedicated test Firebase project. Authenticated user UID comes from token.
exports.vixoQaEnsureCredits = onCall({ region }, async (request) => {
  if (process.env.VIXO_QA_CREDITS_ENABLED !== "true") {
    throw new HttpsError("failed-precondition", "QA credits feature is disabled.");
  }
  if (!request.auth || typeof request.auth.uid !== "string" || !request.auth.uid) {
    throw new HttpsError("unauthenticated", "Sign in first.");
  }
  return ensureQaCredits(request.auth.uid, async (uid, count) => {
    // Separated test collection so we do not overwrite unknown production
    // wallet balances, paid credit purchases, or credit ledger entries.
    await getFirestore().collection("vixoQaCredits").doc(uid).set({
      availableCredits: count,
      source: "owner_qa_fixture",
      updatedAt: FieldValue.serverTimestamp(),
    }, { merge: true });
  });
});
