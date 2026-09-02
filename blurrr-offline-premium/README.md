# Blurrr 2.3.56 offline premium temp patch

Target IPA bundle: `com.pinguo.msgAries`

Input IPA SHA-256:

`968a5b3dba2c70773ffe3f552740207cf23248141f790b2cb216bf1588e1869b`

## Forced runtime state

- `MSUserDefaultHelper.isVip()` -> `true`
- `MSUserDefaultHelper.monthlySVIPIsOpen()` -> `true`
- `PSAutoSubscribeModel.isValid()` -> `true`
- `PSAutoSubscribeModel.isTrialPeriod()` -> `false`
- `PSAutoSubscribeModel.appleVip()` -> `true`
- `PSAutoSubscribeModel.giftVip()` -> `true`
- `PSAutoSubscribeModel.operationVip()` -> `true`
- `MSCheckIAPReceiptModel.isTrialPeriod()` -> `false`
- `MSCheckIAPReceiptModel.appleVip()` -> `true`
- `MSCheckIAPReceiptModel.operationVip()` -> `true`
- `MSCheckIAPReceiptModel.giftVip()` -> `true`

The Boolean gates are replaced with ARM64 `mov w0,#1; ret` or `mov w0,#0; ret`, matching the direct entitlement-gate technique previously used in the YarnPal PoC.

## Packaging

After changing Mach-O code, the original nested/app code signature is stale. Remove `_CodeSignature` from the modified bundle, package it as an unsigned IPA, then sign the IPA with the intended iOS signing method before installation.

The generated test IPA for this branch was archive-verified after repacking and its executable remained `Mach-O 64-bit arm64`.
