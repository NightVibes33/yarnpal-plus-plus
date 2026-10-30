const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { initializeApp } = require("firebase-admin/app");
const { getAuth } = require("firebase-admin/auth");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");
const { isValidLaunchId } = require("./review-utils.cjs");

initializeApp();
const region = "us-central1";

// The only source of privilege is a server-controlled Firebase Auth user and
// Firestore document. Client-supplied booleans NEVER confer premium access.
async function isApprovedReviewUser(uid) {
  if (!uid) return false;
  const [user, doc] = await Promise.all([
    getAuth().getUser(uid),
    getFirestore().collection("vixoReviewAccounts").doc(uid).get(),
  ]);
  const claims = user.customClaims || {};
  return !user.disabled &&
    claims.vixo_app_review === true &&
    claims.vixo_demo_premium === true &&
    doc.exists &&
    doc.get("active") === true &&
    doc.get("premium") === true;
}

exports.vixoReviewAccess = onCall({ region }, async (request) => {
  if (!request.auth) throw new HttpsError("unauthenticated", "Sign in to VIXO first.");
  if (!await isApprovedReviewUser(request.auth.uid)) {
    return { review: false, premium: false };
  }
  return { review: true, premium: true, entitlement: "app_review_demo" };
});

// Every distinct app process launch registers one fresh app-managed device
// session. It does not impersonate a new hardware device or alter StoreKit.
exports.vixoReviewLaunch = onCall({ region }, async (request) => {
  if (!request.auth) throw new HttpsError("unauthenticated", "Sign in to VIXO first.");
  const launchId = request.data?.launchId;
  if (!isValidLaunchId(launchId)) {
    throw new HttpsError("invalid-argument", "launchId must be a UUID.");
  }
  if (!await isApprovedReviewUser(request.auth.uid)) {
    return { review: false, registered: false };
  }
  await getFirestore()
    .collection("vixoReviewSessions")
    .doc(request.auth.uid)
    .collection("launches")
    .doc(launchId)
    .set({
      launchId,
      sessionType: "app_review",
      createdAt: FieldValue.serverTimestamp(),
    }, { merge: true });
  return { review: true, registered: true, launchId };
});
