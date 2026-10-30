// Use only in the Firebase Auth project that actually owns VIXO's account system.
// Never add service-account JSON or user credentials to Git or to an IPA.
import { initializeApp, applicationDefault } from "firebase-admin/app";
import { getAuth } from "firebase-admin/auth";
import { getFirestore, FieldValue, Timestamp } from "firebase-admin/firestore";

const email = process.env.REVIEW_EMAIL?.trim();
const password = process.env.REVIEW_PASSWORD;
const days = Number(process.env.REVIEW_DAYS || "45");
if (!email || !password || password.length < 12) {
  throw new Error("Set REVIEW_EMAIL and REVIEW_PASSWORD (12+ characters).");
}
if (!Number.isInteger(days) || days < 1 || days > 180) {
  throw new Error("REVIEW_DAYS must be 1–180 days.");
}
initializeApp({ credential: applicationDefault() });
const auth = getAuth();
let user;
try {
  user = await auth.getUserByEmail(email);
  if (user.customClaims?.vixo_app_review !== true) {
    throw new Error("Account exists but is not a designated review user; refusing to modify.");
  }
  await auth.updateUser(user.uid, { password, disabled: false });
} catch (error) {
  if (error.code !== "auth/user-not-found") throw error;
  user = await auth.createUser({
    email, password, emailVerified: true, displayName: "VIXO App Review",
  });
}
await auth.setCustomUserClaims(user.uid, {
  ...(user.customClaims || {}),
  vixo_app_review: true,
  vixo_demo_premium: true,
});
await getFirestore().collection("vixoReviewAccounts").doc(user.uid).set({
  active: true,
  premium: true,
  purpose: "app_review",
  expiresAt: Timestamp.fromMillis(Date.now() + days * 86400000),
  updatedAt: FieldValue.serverTimestamp(),
}, { merge: true });
console.log("Active review grant provisioned for UID:", user.uid);
console.log("Never put credentials in the app. Supply them in App Store Connect.");
