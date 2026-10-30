# VIXO — GitHub Actions iOS Simulator full-flow debug

Runs a real iOS Simulator build and an isolated local HTTP backend.
This is an independent **QA harness**, not a rebuild of VIXO's iPhoneOS IPA.

Each app launch logs in two stable QA accounts, registers a new app-owned
process UUID, grants 9,999 **test ledger** credits per account, verifies the
balance, spends 100, and verifies 9,899. It terminates and relaunches the app
to confirm the app UUID rotates while account identity persists.

CI workflow: \`.github/workflows/vixo-simulator-e2e.yml\`, on macOS runner.
Local macOS: \`bash vixo-simulator/run.sh\`. Output JSON and backend ledger
are uploaded as workflow artifacts.

IMPORTANT: The uploaded VIXO 2.2.2 executable has Mach-O
\`LC_BUILD_VERSION.platform=2\` (iPhoneOS). Simulator binaries use platform
\`7\` (iOS Simulator); the existing IPA is not simulator-installable.
To actually run the VIXO application in the simulator, the original
Xcode project, simulator-compatible SDKs and any requisite backend staging
configuration are necessary.

No real backend calls are performed. The QA tokens and server are test-only;
the UUID is an app-managed session identifier, **not** hardware spoofing.
The harness cannot prove real VIXO free-credit policy or unauthorized
production credit grants.
