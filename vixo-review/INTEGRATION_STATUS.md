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

## Binary-confirmed production hostnames (VIXO 2.2.2 IPA)

Static inspection of the supplied `Payload/Vixo.app/Vixo` Mach-O executable found these absolute URLs (URLs alone do not identify auth request paths or authorize access):

- Account/identity host: `https://sg-user.vixo.one`
- Subscription/payment host: `https://sg-pay.vixo.one`
- General API host: `https://api.vixo.one`
- Separately linked SDK/service hosts: `https://paysdk.ldmnq.com`, `https://usersdk.ldmnq.com`

**Consequence:** This app is wired to an existing remote account/payment stack. The `firebase-admin` code in this repository is a non-integrated reference implementation; provisioning a Firebase user is NOT equivalent to provisioning a VIXO account or premium subscription. No privileged access to `sg-user.vixo.one` or `sg-pay.vixo.one` exists in this repository, the uploaded IPA, or the currently linked hosting project. Do not submit the IPA under a claim that this reference adapter unlocks premium features in production.

**Completion prerequisites:** (1) original VIXO source/Xcode project or backend service repository, (2) authorized administrator access to the account and entitlement services, and (3) the app's Apple code-signing/distribution configuration. Without these, do not attempt to manufacture, forge, or locally spoof subscription entitlement or physical device identity. A fresh `virtualDeviceId` is useful for *review session records* only.

**Apple review requirement:** Provide a functioning demo login with full feature access in App Store Connect. For an auto-renewable subscription, provide a second expired-subscription account to exercise the purchase flow. See https://developer.apple.com/help/app-review/before-submitting-for-review/complete-review/ .
