# Existing Site same-origin gateway

The existing owner-private Site is migrated from static hosting to the supported
Vinext/Cloudflare Worker profile. All original GMF assets are retained verbatim
under `public/`; the build copies them to `dist/client/`. The native Sites access
policy remains owner-only. The new Worker only intercepts `/api/v4/*`; every
other request goes to the `ASSETS` binding. It does not replace any module UI.

`worker.ts` and `api-proxy.mjs` are the exact server entry and proxy source.
Set `assets: { binding: 'ASSETS', run_worker_first: true }` in the Cloudflare Vite
configuration and retain the Sites build integration. `route.ts` is an optional
route-handler adapter for installations using app routes; this Site uses the
Worker entry directly.

After the persistent backend is approved, built and its HTTPS readiness passes:

1. Set Sites runtime secrets `GMF_AS_BACKEND_URL` to the actual HTTPS backend
   origin and `GMF_AS_GATEWAY_KEY` to the same secret as backend `GMF_GATEWAY_KEY`.
2. Redeploy the saved gateway version with the new environment revision using
   native Sites tools. No browser code needs an API origin or a service key.
3. Issue the initial admin invitation from the private backend operator CLI;
   register through `/assessment/login.html#invite=...`. Then issue separate
   student invitations. Never use the browser QA users in production.
4. Verify actual password login, PDF/DOCX, full examination and persistence over
   the public HTTPS path. They are still pending until paid hosting is authorized.

Without backend configuration every API path intentionally returns **503 JSON**,
not an HTML fallback or a mock successful response. Anonymous users still pass
through the existing native private Site sign-in gate. The browser receives only
its own Secure/HttpOnly cookie; the proxy forwards only the GMF cookie and selected
headers, never Sites cookies or the platform service token. The backend rejects
direct API calls without its gateway secret and validates Origin + custom header
on mutations. No CORS wildcard is enabled.

Do not set an invented/placeholder backend URL or mark this gateway as a deployed
Python service. Frontend hosting and backend hosting are separate results.
