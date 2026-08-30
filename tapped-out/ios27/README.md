# iPhone 16 / iOS 27 target

This path targets **The Simpsons: Tapped Out 4.69.5**, the final official iOS release.

## Input requirement

Use a user-supplied or otherwise lawfully obtained **4.69.5 IPA**. The old uploaded 4.1.0 IPA is not usable as the executable base because it contains only ARMv7 code.

## Prepare the latest client

```bash
python3 tapped-out/ios27/prepare_latest_ipa.py \
  "Tapped Out 4.69.5.ipa" \
  "Tapped Out 4.69.5-iPhone16-iOS27-unsigned.ipa"
```

The preparation script:

1. validates that the main executable contains ARM64,
2. validates every embedded Mach-O also contains ARM64,
3. removes stale code-signature material,
4. removes obsolete ARMv7-only device-capability declarations when present,
5. repacks a clean unsigned IPA for re-signing.

It intentionally refuses ARMv7-only clients rather than producing an IPA that installs and then fails with `APIInternalError`.

## Preservation/server patching

The current open-source TSTO patcher supports IPA endpoint patching for a replacement game server and DLC server. Keep that endpoint-patching stage separate from architecture preparation so an invalid binary can never reach signing/install.

Recommended flow:

```text
4.69.5 original/authorized IPA
        ↓
ARM64 validation
        ↓
server/DLC endpoint patch
        ↓
remove stale signatures
        ↓
re-sign
        ↓
iPhone 16 / iOS 27
```
