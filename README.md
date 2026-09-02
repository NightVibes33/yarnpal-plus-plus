# Blurrr 2.3.56 Offline Premium + 999999 Juice Temp Build

## Target

**Application:** Blurrr  
**Bundle ID:** `com.pinguo.msgAries`  
**Version:** `2.3.56`  
**Build:** `2356`  
**Platform:** iOS / arm64  
**Branch:** `temp/offline-premium-profile-20260902`

This branch contains the version-locked Blurrr patch and GitHub Actions workflow for producing an unsigned IPA with a hardcoded local premium profile plus a fixed Blurrr Juice balance of `999999`.

## Forced premium state

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

## Forced Blurrr Juice

Static Objective-C metadata in Blurrr 2.3.56 identifies the two signed 64-bit Juice getters used by the account/defaults model:

```text
MSUserDefaultHelper.juiceFromServer()   IMP 0x10065c81c -> 999999
MSUserDefaultHelper.balanceJuice()      IMP 0x10065cdbc -> 999999
```

Both getters are patched so normal account/server refreshes cannot reduce the locally observed Juice balance.

The ARM64 return sequence loads decimal `999999` (`0x0F423F`) into `x0` and returns:

```asm
movz x0, #0x423f
movk x0, #0x000f, lsl #16
ret
```

## Verification

Reference user-supplied IPA SHA-256:

```text
968a5b3dba2c70773ffe3f552740207cf23248141f790b2cb216bf1588e1869b
```

The workflow validates:

- bundle ID `com.pinguo.msgAries`
- version `2.3.56`
- build `2356`
- exact expected ARM64 instruction windows for every premium and Juice patch
- post-write bytes for every patch location
- IPA ZIP integrity after repackaging

## Branch contents

```text
.github/workflows/publish-blurrr-temp-release.yml
blurrr-offline-premium/patch.py
blurrr-offline-premium/OfflinePremiumProfile.json
blurrr-offline-premium/README.md
```

## GitHub Release

Every push to this temp branch triggers the release workflow. It downloads the known Blurrr 2.3.56 source asset, verifies the app identity, applies the premium + `999999` Juice patches, removes stale signature material, repackages the app, and publishes:

```text
BlurrrPremium-2.3.56-unsigned.ipa
BlurrrPremium-2.3.56-unsigned.sha256
```

Release tag:

```text
blurrr-offline-premium-2.3.56-temp
```

## Signing

The generated IPA is intentionally unsigned because Mach-O modification invalidates the original Apple code signature. Re-sign the IPA with the intended iOS signing certificate before installation.
