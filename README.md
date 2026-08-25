# YarnPal iOS Premium Entitlement Bypass PoC

## Summary

**Application:** YarnPal  
**Bundle ID:** `com.knitpal.knitcrochet`  
**Tested Version:** `1.51`  
**Platform:** iOS  
**Issue:** Client-side premium entitlement bypass  
**Impact:** Premium state can be forced entirely on-device without a valid subscription, successful StoreKit transaction, or server-issued premium entitlement.

During security testing of YarnPal 1.51, the application's premium authorization flow was found to rely on client-side Boolean entitlement checks exposed through its account frameworks.

By modifying the return values of several client-side entitlement methods, YarnPal accepts the local process as a premium account and exposes premium functionality without requiring successful server-side verification.

---

## Vulnerability

YarnPal exposes premium status through methods including:

```text
GLMediator.Account_IsVip()
GLMediator.Account_IsFakeVip()

GLMPAccount.isVip()
GLMPAccount.isFakeVip()
GLMPAccount.isTrial()
```

The important discovery was that premium-facing application modules query the mediator-level API:

```text
GLMediator.Account_IsVip()
```

If this method reports `true`, the application treats the current account/session as premium.

This means a mutable client-side Boolean result is being used as an authorization decision.

---

## Working PoC

The successful proof of concept modified the client-facing entitlement checks so that they reported:

```text
Account_IsVip()      = true
Account_IsFakeVip()  = true

isVip()              = true
isFakeVip()          = true
isTrial()            = false
```

Conceptually, the critical authorization method becomes equivalent to:

```c
bool Account_IsVip(void) {
    return true;
}
```

At the ARM64 level, the test implementation was equivalent to:

```asm
mov w0, #1
ret
```

No valid StoreKit purchase was performed.

No premium subscription receipt was created.

No premium account was required.

---

## Result

After installing the modified test build, YarnPal treated the test environment as premium.

Observed behavior:

```text
Valid subscription:      NO
StoreKit purchase:       NO
Server premium grant:    NO

Account_IsVip():         TRUE
Premium functionality:  AVAILABLE
```

This demonstrates that premium authorization can be satisfied entirely through manipulation of application-controlled client state.

---

## Important Finding During Testing

Initially, only the lower-level function:

```text
GLMPAccount.isVip()
```

was modified.

That alone did **not** unlock premium functionality.

Further analysis showed that several YarnPal modules query the account system through:

```text
GLMediator.Account_IsVip()
```

rather than directly invoking:

```text
GLMPAccount.isVip()
```

Once the mediator-level entitlement check was modified to return `true`, premium functionality became available.

This establishes:

```text
GLMediator.Account_IsVip()
```

as a significant premium authorization entry point.

---

## Entitlement Architecture

Static analysis also identified YarnPal's persisted VIP model:

```text
GLAccount.PersistenceModel.vipInfo
```

with the preference identifier:

```text
kAccountVipInfoKey
```

and a serialized:

```text
GLAPIVipInfo
```

object.

Relevant properties include:

```text
is_vip
is_trial
is_auto_renew
is_vip_in_history
is_paid_in_history
is_refund_in_history
is_trial_and_expired
vip_level
sku
start_at
expired_at
purchase_subscription_skus
```

The normal entitlement flow appears similar to:

```text
StoreKit / Backend
        |
        v
GLAPIVipInfo
        |
        v
PersistenceModel.vipInfo
        |
        v
GLMPAccount
        |
        v
GLMediator.Account_IsVip()
        |
        v
Premium UI / Features
```

The security weakness exists because the final authorization boundary remains controllable within the client process.

---

# Reproduction

## 1. Obtain an Authorized Test Build

Testing was performed against:

```text
YarnPal 1.51
com.knitpal.knitcrochet
```

The application was decrypted for authorized research.

---

## 2. Locate Relevant Frameworks

Relevant components include:

```text
GLAccountExtension.framework
GLMP.framework
```

The successful PoC required modification of the mediator-facing entitlement logic rather than only the lower-level account helper.

---

## 3. Modify Entitlement Decisions

For the PoC, the relevant entitlement methods were made to report:

```text
GLMediator.Account_IsVip()      -> true
GLMediator.Account_IsFakeVip()  -> true

GLMPAccount.isVip()             -> true
GLMPAccount.isFakeVip()         -> true
GLMPAccount.isTrial()           -> false
```

The critical result was forcing the mediator-level VIP decision.

The equivalent ARM64 Boolean-return implementation is:

```asm
mov w0, #1
ret
```

For methods that should return `false`:

```asm
mov w0, #0
ret
```

---

## 4. Re-Sign the Application

Because modifying framework executables invalidates their original code signatures, the application and affected nested frameworks must be correctly re-signed before installation.

Testing showed that signing/install tooling can materially affect whether the modified application launches.

---

## 5. Install and Launch

Install the authorized modified build and launch YarnPal without purchasing Premium.

---

## 6. Observe

The application recognizes the test environment as premium and exposes premium functionality despite the absence of a legitimate premium entitlement.

---

# Signing / SideStore Note

An unrelated installation issue occurred during testing that initially appeared to be an application crash.

A test IPA installed through SideStore failed to launch correctly.

The entitlement modifications themselves were later confirmed to work after the IPA was signed and installed using ESign with a valid signing certificate.

This indicates that the SideStore failure was related to the signing/install process rather than the underlying entitlement finding.

Therefore:

```text
SideStore launch failure != entitlement bypass failure
```

The confirmed PoC result was obtained after correctly signing the modified application.

---

# Failed Approaches / Research Notes

## Local Preferences Modification

The following entitlement persistence location was identified:

```text
Library/Preferences/com.knitpal.knitcrochet.plist
```

with:

```text
kAccountVipInfoKey
```

containing a `GLAPIVipInfo` representation.

An initial test attempted to modify:

```text
kAccountVipInfoKey
└── is_vip = true
```

This did not reliably result in premium access.

One likely contributing factor is that YarnPal accesses this state through `NSUserDefaults`, meaning the running application may receive state managed by `cfprefsd` rather than immediately consuming direct file changes.

This test therefore did not provide a reliable entitlement bypass.

---

## Patching Only GLMPAccount.isVip()

A second test forced:

```text
GLMPAccount.isVip() -> true
```

This also did not provide premium access.

Further analysis demonstrated that premium-facing modules use:

```text
GLMediator.Account_IsVip()
```

as a caller-facing authorization API.

This was a key distinction.

---

## Mediator-Level Patch

The successful test forced:

```text
GLMediator.Account_IsVip() -> true
```

Once this mediator-level decision reported VIP status, YarnPal exposed premium functionality.

This confirmed that the mediator API forms part of the effective authorization boundary.

---

# Security Impact

The issue breaks the expected trust boundary protecting paid functionality.

An attacker capable of modifying and re-signing the iOS application can potentially cause YarnPal to report a premium entitlement without possessing a legitimate subscription.

Depending on which functionality is available offline or lacks additional backend authorization, this could allow unauthorized access to features intended to require payment.

The expected authorization property should resemble:

```text
trustedPurchaseOrServerEntitlement == true
```

Instead, the effective authorization decision can be reduced to:

```text
clientControlledBoolean == true
```

A Boolean controlled entirely by the client process should not be considered a trustworthy authorization primitive.

---

# Root Cause

The core issue is excessive reliance on **client-side premium authorization**.

`GLMediator.Account_IsVip()` and related methods are treated as authoritative even though they execute entirely inside an application process that can be modified by an attacker.

The application therefore does not maintain a sufficiently strong separation between:

```text
premium display/state information
```

and:

```text
authorization to perform premium operations
```

Manipulating the former can influence the latter.

---

# Attack Flow

A simplified attack path is:

```text
Modified iOS Application
        |
        v
Patch Account_IsVip()
        |
        v
Return TRUE
        |
        v
GLMediator reports VIP
        |
        v
Premium-facing modules trust result
        |
        v
Premium functionality becomes available
```

No legitimate subscription is required for the manipulated client-side decision.

---

# Recommended Remediation

Local state may still be used to display premium status, but sensitive premium operations should not rely exclusively on client-controlled Boolean methods.

A stronger architecture would be:

```text
StoreKit Transaction
        |
        v
Signed Transaction Verification
        |
        v
Backend Validation
        |
        v
Server-Side Entitlement
        |
        v
Authenticated Entitlement Artifact
        |
        v
Premium Operation
```

For functionality that must remain available offline, use a locally cached entitlement artifact that is cryptographically authenticated.

For example:

```json
{
  "userID": "example-user",
  "entitlement": "premium",
  "productID": "premium.subscription",
  "issuedAt": 1760000000,
  "expiresAt": 1762592000,
  "deviceBinding": "optional-device-or-account-binding"
}
```

The entitlement payload should be accompanied by a server-generated digital signature.

The application can verify the artifact offline using an embedded public key.

Changing a local value such as:

```text
isVip = true
```

or forcing:

```text
Account_IsVip() = true
```

should not be sufficient to manufacture a valid premium entitlement.

---

# Defense in Depth

Additional hardening could include:

- Verify StoreKit 2 signed transactions rather than trusting locally generated state.
- Validate entitlement state server-side for premium network operations.
- Separate UI presentation state from authorization decisions.
- Avoid using a single Boolean helper as an authoritative paid-feature gate.
- Authenticate offline entitlement caches cryptographically.
- Include entitlement expiration timestamps in signed server-issued data.
- Revalidate entitlement when connectivity returns.
- Treat locally persisted VIP state as a cache only, never as authoritative proof of purchase.
- Ensure backend APIs independently enforce premium authorization.
- Add regression tests that intentionally force `Account_IsVip()` and verify sensitive premium operations remain inaccessible without a valid entitlement.

---

# Suggested Classification

## CWE-602

**Client-Side Enforcement of Server-Side Security**

The application relies on client-side state to enforce an authorization decision that should ultimately be derived from a trusted purchase or server-side entitlement.

## CWE-353

**Missing Support for Integrity Check**

This may also apply if locally persisted entitlement information is trusted without cryptographic integrity protection.

---

# Suggested Severity

**Medium to High**

Severity depends on:

- which premium functionality becomes available
- whether premium functionality works entirely offline
- whether premium network APIs independently validate authorization
- whether premium content itself can be retrieved without server verification
- whether the issue affects only cosmetic UI state or actual paid resources
- whether subscription-only functionality can be executed successfully

If all significant paid functionality becomes usable solely because the client reports:

```text
Account_IsVip() == true
```

then the impact is substantially higher.

---

# Evidence of Successful Exploitation

The following sequence was observed during testing:

```text
1. Start with YarnPal 1.51 without a premium subscription.

2. Modify the account entitlement framework.

3. Force:

   GLMediator.Account_IsVip() = true

4. Correctly re-sign and install the application.

5. Launch YarnPal.

6. Observe that premium functionality becomes available.
```

The same result was not obtained when modifying only the lower-level:

```text
GLMPAccount.isVip()
```

which further demonstrates the importance of the mediator-level authorization path.

---

# One-Line Finding

> YarnPal 1.51 allows premium authorization to be bypassed by manipulating the client-side `GLMediator.Account_IsVip()` entitlement decision, causing the application to enter a premium state without a valid StoreKit subscription or server-issued entitlement.

---

# Testing Scope

This proof of concept was produced for authorized security testing.

The purpose of the PoC is to demonstrate that the current client-side entitlement boundary can be manipulated and to provide sufficient technical information for remediation and regression testing.

No production user accounts, unauthorized third-party accounts, or unrelated systems were required to demonstrate the issue.
