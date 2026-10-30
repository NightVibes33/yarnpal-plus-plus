# VIXO 2.2.2 integration: what is verified vs. blocked

## Verified from uploaded IPA
- Executable is Mach-O arm64, bundle ID `sg.com.vixo.app`, version `2.2.2`.
- Contains FirebaseAuth; this **does not establish** that Firebase Auth controls VIXO business login.
- Embedded `Architecture.md` says the original sources are under `Vixo/Vixo/BizScenes` and `SharePods`; Account/Subscription are in Settings.
- Binary includes `VixoLoginViewController`, `VixoSubscriptionAccountService`, `LDUserCenterKit`, and `SubscribeUILib`.
- The connected YarnPal repo contains NO original VIXO source or server/backend.

## Implemented in this branch
- A Firebase-based review entitlement reference backend with identity allowlisting, a time-limited premium grant, revoke procedure and unit tests.
- A new **virtual review-device ID** is recorded each app process launch, only for an approved review user. The device's real identity is unchanged.
- A Swift coordinator hook to call AFTER the *real VIXO* login. This is integration code, not a patch to a compiled executable.
- Automated JS tests, with a separate Swift syntax/typecheck performed outside GitHub Actions.

## Cannot be completed from this IPA and YarnPal README
- Provision an online VIXO account: requires privileged access to the **real** account backend. The Firebase client plist in the IPA is not administrator credentials.
- Make VIXO premium truly work: must grant entitlement through VIXO's authoritative subscription service and authorize premium server operations.
- Alter the shipped IPA, sign a new App Store distribution build, or submit it: original Xcode project and App Store Connect signing/deployment access are absent.
- Make Apple or hardware/device-tracking services treat real iOS hardware as new: an app-generated ID cannot spoof those external identities.

## Exact source integration points
1. Find the actual implementation of `VixoSubscriptionAccountService` and the API that authorizes premium operations; merge authorized review grants **server side**.
2. In the existing `VixoLoginViewController` login restoration/success path, call `VixoReviewCoordinator.initializeAfterLogin()`, using the account's existing token provider.
3. Inside backend Account/Subscription endpoints, allow short-lived review entitlements only for authenticated, explicitly allowlisted reviewers. Do not use an unconditional local `isPremium = true`.
4. Register virtual-device ID once per process in VIXO's own backend session/device registry; do not overwrite IDFV, advertising IDs, Keychain IDs, purchase receipts, or Firebase installation IDs.
5. Create the account in the backend and enter its credentials in App Store Connect's review instructions, verify all premium features, then submit a signed distribution build.

**Do not deploy the Firebase example to project `vixo-96e94` until its owner has explicitly verified that Firebase Auth is the actual user identity authority and provided authorized admin credentials.**
