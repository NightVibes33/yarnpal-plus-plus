# VIXO 2.2.2 — Entire IPA static inspection

Read-only analysis of the supplied decrypted VIXO 2.2.2 IPA, not a modification or distribution build.

## Coverage
- Main app, VixoPushExtension and eight embedded dynamic frameworks: **10/10 Mach-O images** parsed.
- **1,134** packaged entries; **86** privacy manifests.
- **57,824** decoded Objective-C method records; **56,864** associated with an owning class/metaclass.
- The executable imports **119** dynamic libraries/frameworks. The original architecture documentation identifies Create/Freely, AssetLibrary, Opus, Mine, Settings, Account and Subscription modules.
- The complete inventory and class-method index were saved separately as local downloadable artifacts, rather than committing proprietary binary-derived metadata to this public repository.

## Evidence
- Bundle ID: `sg.com.vixo.app`, build `2026102007`, minimum iOS 15.6.
- `VixoDeviceIDSandboxCacheKey` string at ARM64 VA `0x102b710d0`; one ADRP+ADD reference validated at `0x10009fe80`/`0x10009fe84`.
- A previous heuristic candidate `0x1000c135c` was a **false positive** and was excluded after disassembly.
- The methods `createDeviceIdentifierAndlinkDevice`, `checkinDeviceIDFromKeychainContent:`, and decoded Objective-C `isNewUser` belong to third-party AdMob/Firebase SDK classes, not verified VIXO credit logic.
- The app includes separate account, payment and API host strings: `sg-user.vixo.one`, `sg-pay.vixo.one` and `api.vixo.one`. An embedded host is not proof of an active endpoint or eligibility algorithm.
- All 10 images contain embedded code-signature blobs, but CodeDirectory page hashes **do not fully match** the provided decrypted bytes. Loader validity, re-signing and on-device behavior were not verified.
- No SatellaJailed or AutoRcSideload dylib is embedded. Their installed analysis skill's precomputed function/call graphs cannot be substituted for this unrelated app's code.

## Implementation status
- The existing `vixo-review/` sources are a **standalone server-backed review account test adapter** and an app launch/session record utility. They are not integrated into the compiled VIXO executable or its real account/subscription backend.
- Rotating a client UUID cannot prove that a real device is new, nor automatically change the user's server account or credit-grant record.
- No modified IPA was produced, signed, installed or successfully exercised with a production credit response.

## Required end-to-end validation
Access to the **original Xcode source**, the **authorized VIXO account/subscription backend** and a **signed test build** is needed to implement and verify a legitimate App Review test identity or credit fixture. A true live backend response and device runtime trace are necessary before claiming any credit change or identity registration is working.

This document is static evidence only and should not be represented as a successful app bypass, verified purchase entitlement, signed build or deployed service.
