# VIXO App Review integration (source adapter; not yet deployed)

This branch contains server-side entitlement and app-launch registration **source** for legitimate Apple App Review testing. The uploaded VIXO v2.2.2 IPA is a compiled binary; neither VIXO's Xcode source nor privileged backend credentials are in this repo.

## Recommended production integration

Use the existing VIXO login and subscription backend as the authority. The IPA contains `VixoLoginViewController`, `VixoSubscriptionAccountService`, `LDUserCenterKit` and `SubscribeUILib`. Add `ios/VixoReviewCoordinator.swift` to the original source; implement `VixoReviewBackend` using the actual account/subscription service, server-approved premium access, and the server's virtual-device registration. Call it after login or session restore. The coordinator generates a new app-managed UUID each app process, so the server can register a fresh **virtual review-device record** for the authorized reviewer. It does not impersonate a new physical device.

A valid online premium review account must be created in the original auth/subscription backend, with real entitlement enforcement on every premium API. Credentials should be supplied privately to Apple through App Store Connect; do not hardcode the email/password inside a production IPA.

## Optional Firebase Auth reference implementation

Only if Firebase Auth really owns VIXO user accounts:
1. Use an authorized Firebase admin account and the right Firebase project.
2. `cd backend && npm install`; configure `GOOGLE_APPLICATION_CREDENTIALS` to a private service-account JSON, `REVIEW_EMAIL`, `REVIEW_PASSWORD` (12+ characters), optionally `REVIEW_DAYS` (default 45), then `npm run provision`. No credentials are checked in.
3. Deploy Cloud Functions using `firebase deploy --config firebase.json --only functions:vixoReviewAccess,functions:vixoReviewLaunch --project <AUTHORIZED_PROJECT>`. Confirm the project's existing functions setup/codebase first.
4. The optional `ios/ReviewAccessService.swift` uses Firebase callable functions. It is **not a substitute** for the business login when VIXO uses an independent account service.
5. Backend premium endpoints must also validate the review grant. The functions alone cannot grant actual original-backend premium operations.
6. Smoke-test the App Store review credentials, normal purchases, premium operations and expiry. For revocation, `cd backend && npm run revoke` using `REVIEW_EMAIL`.

Run offline unit checks: `cd functions && node --test`.

Read `INTEGRATION_STATUS.md` for verified evidence, limitations and precise source hooks.
