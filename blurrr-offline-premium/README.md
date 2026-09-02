# Blurrr 2.3.56 offline premium + 999999 Juice temp patch

Target IPA bundle: `com.pinguo.msgAries`

Reference uploaded IPA SHA-256:

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
- `MSUserDefaultHelper.juiceFromServer()` -> `999999`
- `MSUserDefaultHelper.balanceJuice()` -> `999999`

The Boolean gates use ARM64 `mov w0,#1; ret` / `mov w0,#0; ret`. The Juice getters are signed 64-bit (`q16@0:8`) and are replaced with an ARM64 sequence that returns decimal `999999` in `x0` before `ret`.

Patching both Juice getters keeps the local balance fixed even when normal account/server-refresh code updates the underlying stored value.

## Packaging

After changing Mach-O code, the original nested/app code signature is stale. `_CodeSignature` and the embedded provisioning profile are removed before packaging the unsigned IPA. Sign the resulting IPA with the intended iOS signing method before installation.

The local generated IPA was archive-verified after repacking and both Juice patch windows were re-read successfully.
