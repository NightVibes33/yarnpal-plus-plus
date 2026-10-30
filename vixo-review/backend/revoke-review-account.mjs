import { initializeApp, applicationDefault } from "firebase-admin/app";
import { getAuth } from "firebase-admin/auth";
import { getFirestore, FieldValue } from "firebase-admin/firestore";

const email = process.env.REVIEW_EMAIL?.trim();
if (!email) throw new Error("Set REVIEW_EMAIL to revoke the demo account.");
initializeApp({ credential: applicationDefault() });
const auth = getAuth();
const user = await auth.getUserByEmail(email);
if (user.customClaims?.vixo_app_review !== true) {
  throw new Error("Refusing to modify a non-review account.");
}
// Deny immediately via Firestore gate even if an older ID token survives.
await getFirestore().collection("vixoReviewAccounts").doc(user.uid).set({
  active: false, premium: false, updatedAt: FieldValue.serverTimestamp(),
}, { merge: true });
const claims = { ...(user.customClaims || {}) };
delete claims.vixo_app_review;
delete claims.vixo_demo_premium;
await auth.setCustomUserClaims(user.uid, claims);
await auth.updateUser(user.uid, { disabled: true });
await auth.revokeRefreshTokens(user.uid);
console.log("Revoked review account UID:", user.uid);
