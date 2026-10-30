// Server/admin command; never run in the app and never commit credentials.
import { initializeApp, applicationDefault } from "firebase-admin/app";
import { getAuth } from "firebase-admin/auth";
import { getFirestore, FieldValue } from "firebase-admin/firestore";

const email = process.env.REVIEW_EMAIL?.trim();
const password = process.env.REVIEW_PASSWORD;
if (!email || !password || password.length < 12) {
  throw new Error("Set REVIEW_EMAIL and REVIEW_PASSWORD (at least 12 characters).");
}
initializeApp({ credential: applicationDefault() });
const auth = getAuth();
let user;
try {
  user = await auth.getUserByEmail(email);
  if (user.customClaims?.vixo_app_review !== true) {
    throw new Error("Email belongs to a non-review account; refusing to overwrite it.");
  }
  await auth.updateUser(user.uid, { password, disabled: false });
} catch (error) {
  if (error.code !== "auth/user-not-found") throw error;
  user = await auth.createUser({
    email, password, emailVerified: true, displayName: "VIXO App Review",
  });
}
// Claim state and the document must BOTH permit review access.
await auth.setCustomUserClaims(user.uid, {
  ...(user.customClaims || {}),
  vixo_app_review: true,
  vixo_demo_premium: true,
});
await getFirestore().collection("vixoReviewAccounts").doc(user.uid).set({
  active: true,
  premium: true,
  email,
  updatedAt: FieldValue.serverTimestamp(),
}, { merge: true });
console.log("Review account provisioned for UID:", user.uid);
console.log("Do not put the password in your IPA; supply it via App Store Connect review info.");
