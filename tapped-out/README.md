# Tapped Out iOS offline-profile workbench

Temporary branch workspace for the uploaded `Tapped Out (v4.1.0).ipa`.

## Verified blocker

The uploaded IPA contains a **thin armv7-only** Mach-O executable:

- Bundle ID: `com.ea.simpsonssocial.inc2`
- Version: `4.1.0`
- SDK: `iphoneos6.0`
- Minimum iOS: `4.3`
- Main executable architecture: `armv7`

Current iOS devices that accept only `arm64`/`arm64e` cannot execute this binary. Re-signing, changing `Info.plist`, changing the Mach-O CPU header, or repackaging the IPA cannot translate ARMv7 instructions into ARM64 instructions.

**Required to get the real game running on a modern device:** an ARM64 Tapped Out client executable or buildable source code.

## Offline/premium state discovered in the 4.1.0 client

Static strings in the uploaded client confirm code paths for:

- `CachedUserData`
- `/cachedUser`
- anonymous login
- `premiumCurrency`
- `donuts`
- read/spend/award/collect currency handlers
- premium unlock entities

The recovered Tapped Out protobuf schema used by community preservation servers also exposes `CurrencySaveData` with `money`, `premium`, `realMoney`, and `realPremium` fields. The target hardcoded profile is in `profile/offline-profile.json`.

That JSON is a **target contract**, not a claim that the ARMv7 binary currently consumes it. It should be wired into an ARM64 client/source build at the account/cached-user and currency boundaries so remote authentication and purchase state are not required for the offline build.

## Tools

Run:

```bash
python3 tools/inspect_ipa.py path/to/app.ipa
```

The tool exits non-zero when the main executable lacks an ARM64 slice.
