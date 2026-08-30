# Tapped Out 4.69.5 — offline profile / currency reverse map

Target: **The Simpsons: Tapped Out 4.69.5** on **iPhone 16 / iOS 27 / arm64**.

This file preserves the account/currency findings used by the offline preservation build and separates what is already confirmed by the recovered TSTO protocol from strings that must be verified directly in a 4.69.5 IPA.

## Offline account state

### Confirmed protocol structures

Recovered TSTO protobuf definitions expose:

```text
UserIndirectData
  userId
  telemetryId

AnonymousUserData
  isAnonymous

TokenData
  sessionKey
  expirationDate

UsersResponseMessage
  user
  token
```

These structures establish an anonymous/local-account path that can be represented without a normal named EA account in a preservation/private-server build.

### Client markers carried forward for 4.69.5 verification

The older client analysis identified:

```text
CachedUserData
cachedUser
/cachedUser
anonymous
```

Run:

```bash
python3 tapped-out/tools/scan_4695_markers.py TappedOut-4.69.5.ipa --json scan-4695.json
```

to record their exact presence/file/offset in the 4.69.5 client. Do not copy offsets from the 4.1.0 binary; they are version-specific.

## Currency / donuts

### Confirmed protocol structures

The recovered TSTO protocol exposes:

```text
CurrencySaveData
  money
  premium
  realMoney
  realPremium
  numSpecial
  specialType
  specialAmount
```

It also exposes response/update structures including:

```text
CurrencyResponseMessage
  currency
  error

GambleResponse
  updatedCurrency
  currencyAwarded
  error
```

The offline profile contract therefore maps the local premium balance to:

```text
premium = 2,000,000,000
```

and uses the human-facing alias:

```text
donuts = 2,000,000,000
```

The JSON contract is:

```text
tapped-out/profile/offline-profile.json
```

## Client-side marker set for 4.69.5

The scanner searches the 4.69.5 IPA for:

```text
CachedUserData
cachedUser
/cachedUser
AnonymousUserData
isAnonymous
premiumCurrency
premium
realPremium
donuts
Donuts
CurrencyData
CurrencySaveData
CurrencyResponseMessage
updatedCurrency
currencyAwarded
spend
award
collect
```

For every hit it records:

- IPA member path
- byte offset
- printable surrounding context
- category

This provides a reproducible replacement for the older ad-hoc string findings.

## Offline profile target behavior

The preservation/private-server client profile is defined as:

```text
authentication.required = false
authentication.anonymous = true
authentication.networkRequired = false
authentication.preferCachedUser = true

entitlements.forcePremium = true
entitlements.premiumEnabled = true
entitlements.purchasesRequired = false

currency.money = 2,000,000,000
currency.premium = 2,000,000,000
currency.donuts = 2,000,000,000

persistence.saveLocally = true
persistence.preferLocalOverRemote = true
persistence.remoteSyncEnabled = false
persistence.cachedUserEnabled = true
```

## Architecture gate

Before any 4.69.5 client is used, run:

```bash
python3 tapped-out/tools/inspect_ipa.py TappedOut-4.69.5.ipa
```

The verifier requires:

```text
CFBundleShortVersionString == 4.69.5
main executable contains arm64
all embedded Mach-O binaries contain arm64
```

This is the compatibility gate for iPhone 16 / iOS 27.
