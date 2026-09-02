# Blurrr 2.3.56 Offline Premium Temp Build

## Target

**Application:** Blurrr  
**Bundle ID:** `com.pinguo.msgAries`  
**Version:** `2.3.56`  
**Platform:** iOS / arm64  
**Branch:** `temp/offline-premium-profile-20260902`

This branch contains the version-locked patch and GitHub Actions workflow for producing an unsigned Blurrr 2.3.56 IPA with a hardcoded local premium profile.

## Offline premium state

The patch forces the relevant client-side entitlement paths into a paid state:

```text
MSUserDefaultHelper.isVip()                   -> true
MSUserDefaultHelper.monthlySVIPIsOpen()       -> true

MSCheckIAPReceiptModel.isTrialPeriod()        -> false
MSCheckIAPReceiptModel.appleVip()             -> true
MSCheckIAPReceiptModel.operationVip()         -> true
MSCheckIAPReceiptModel.giftVip()              -> true

PSAutoSubscribeModel.isValid()                -> true
PSAutoSubscribeModel.isTrialPeriod()          -> false
PSAutoSubscribeModel.appleVip()               -> true
PSAutoSubscribeModel.giftVip()                -> true
PSAutoSubscribeModel.operationVip()           -> true
```

Boolean return gates are replaced directly in the ARM64 executable with:

```asm
mov w0, #1
ret
```

for enabled premium state, and:

```asm
mov w0, #0
ret
```

for trial-state checks that must remain disabled.

## Source verification

The patch is intentionally locked to the tested Blurrr IPA:

```text
Bundle:  com.pinguo.msgAries
Version: 2.3.56
Input SHA-256:
968a5b3dba2c70773ffe3f552740207cf23248141f790b2cb216bf1588e1869b
```

The workflow refuses to patch a source IPA when its SHA-256, bundle identifier, or app version does not match the expected Blurrr 2.3.56 build.

## Branch contents

```text
.github/workflows/publish-blurrr-temp-release.yml
blurrr-offline-premium/patch.py
blurrr-offline-premium/OfflinePremiumProfile.json
blurrr-offline-premium/README.md
```

### `patch.py`

Contains the exact version-locked ARM64 offsets and entitlement-return replacements.

### `OfflinePremiumProfile.json`

Documents the intended local state:

```json
{
  "mode": "offline-premium-hardcoded",
  "vip": true,
  "svipFeatureGate": true,
  "subscriptionValid": true,
  "trial": false,
  "appleVip": true,
  "operationVip": true,
  "giftVip": true,
  "expirationPolicy": "ignored-by-patched-validity-gate"
}
```

## GitHub Release workflow

Every push to this temp branch triggers:

```text
.github/workflows/publish-blurrr-temp-release.yml
```

The workflow:

1. Checks out `temp/offline-premium-profile-20260902`.
2. Obtains the Blurrr 2.3.56 source IPA.
3. Verifies the exact SHA-256, bundle ID, and version.
4. Extracts the IPA.
5. Applies the offline VIP/SVIP patch.
6. Removes stale code-signature data from the modified bundle.
7. Repackages the app as:

```text
BlurrrPremium-2.3.56-unsigned.ipa
```

8. Verifies ZIP integrity and generates a SHA-256 file.
9. Publishes both files to the GitHub Release tag:

```text
blurrr-offline-premium-2.3.56-temp
```

## Signing

The generated IPA is intentionally unsigned. Modifying the Mach-O executable invalidates the original Apple code signature.

Sign `BlurrrPremium-2.3.56-unsigned.ipa` with the intended iOS signing certificate before installing it on a device.

## Expected result

The patched executable locally reports a valid paid VIP/SVIP state without relying on the normal trial flag or local subscription-validity result.

Server-authorized functionality can still independently require backend authorization; the patch specifically targets the client-side premium state present in this Blurrr build.
