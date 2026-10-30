# VIXO QA — iPhoneOS build

This GitHub Actions job builds a separate, standalone iPhoneOS ARM64 QA app,
not a patched, re-signed or executable replacement for the supplied
\`sg.com.vixo.app\` VIXO 2.2.2 IPA.

**Included features:**
- New app-controlled UUID on every process launch; does not change iOS hardware ID.
- Two isolated fixture accounts. Each QA login resets its locally stored credit
  balance to **9,999 TEST credits**. Spending 100 QA credits decrements the local
  fixture ledger, which remains on the user's device.
- A strictly **read-only GET** to
  \`https://api.vixo.one/api/rest/user/points/info\`. The app displays the HTTP
  status only; no response body is read or displayed.
- Clear on-screen QA labeling. No real VIXO purchases, paid credits, login or
  credit grants.

**Build:** \`bash vixo-device/build-ipa.sh\` on a macOS machine with Xcode/iPhoneOS
SDK; or run \`.github/workflows/vixo-device-ipa.yml\`. GitHub Actions uploads
\`Vixo-QA-iPhoneOS-UNSIGNED.ipa\`.

The device artifact is **ad-hoc signed only**. It has no Apple team-based
provisioning profile; it is **not installable on an ordinary iPhone until
re-signed** with a valid iOS certificate/profile using an authorized tool.

The original VIXO IPA and its actual backend cannot be rebuilt or modified from
this repo. The app's real account/credit/entitlement API is not connected; this
build does not grant credits to production users.

The iOS Simulator end-to-end HTTP test lives separately in
\`vixo-simulator/\`. It already passed in GitHub Actions and is not bundled
into this device IPA.
