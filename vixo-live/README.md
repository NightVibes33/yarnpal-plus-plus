# VIXO compiled-IPA API: production read-only probe

**Observed in the supplied VIXO 2.2.2 executable**, not verified
against the live production backend:

- \`https://sg-user.vixo.one\`: account host candidate
- \`https://sg-pay.vixo.one\`: payments/credits host candidate
- \`https://api.vixo.one\`: general API host candidate
- \`/api/rest/user/points/info\`: user credit balance route string
- \`/api/rest/user/points/bookPage\`: credit history route string
- \`/api/rest/user/info\`: user profile route string

This project probes only HTTPS host reachability and an **unauthenticated
GET** against the user-points-info path; the endpoint's real HTTP method,
authentication and response schema are not confirmed by binary strings.
The probe logs *status and content-type*, never HTTP body, cookies or keys.
A 200 response is not proof the account is authenticated, or that credits
are spendable. A 401/403 means the server rejected this anonymous request,
not that the API is unusable by a signed-in app.

Run \`node --test vixo-live/probe.test.mjs\`, then
\`node vixo-live/probe.mjs --json-file vixo-live/qa-results.json\`.
CI workflow \`.github/workflows/vixo-live-readonly.yml\` repeats this on a
GitHub-hosted runner and uploads the status-only JSON.

The iOS Simulator harness has also been updated to exercise the *observed*
\`/api/rest/user/points/info\` path against its isolated QA server, without
calling production. This validates only client path construction and
fixture behavior; it is **not** a real VIXO account login.

For actual production credit reconciliation, the authorized VIXO account
service must supply a logged-in session and the documented read-only balance
API contract. Changing, granting or replaying credits requires the
owner's permissioned server-side ledger API. **None is available from a
compiled IPA or anonymous health check.**
