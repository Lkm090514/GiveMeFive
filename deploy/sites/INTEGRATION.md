# Same-origin adapter (prepared, not activated)

Keep this Site's identity, access policy, full assets and URLs. Do not change audience.
After the persistent backend is approved and its HTTPS health/readiness pass:

1. Open the existing owner-private Site using its source helper. Migrate its static profile to the supported Vinext starter following Sites' static-to-Worker guidance; preserve existing `dist/` resources as static `public/` assets. Never substitute a fresh UI or omit textbook assets.
2. Copy `api-proxy.mjs` and `route.ts` beside each other into `app/api/v4/[...path]/`. The route is server-only; never import the proxy into client code.
3. Set Sites runtime secrets `GMF_AS_BACKEND_URL` (the actual backend HTTPS origin) and `GMF_AS_GATEWAY_KEY`; set the same key as backend `GMF_GATEWAY_KEY`. They must never be in hosting.json, HTML or browser storage.
4. Build/package using the Sites helpers. Verify the entire original runtime manifest and authenticated asset access. Publish owner-private. These source files alone do not activate the proxy.
5. Health/API test must return JSON at the existing `/api/v4/*` paths; an anonymous call must fail. Exercise actual login in Safari.

The browser stores only its own Secure/HttpOnly session cookie on the GMF origin. Sites sign-in remains the outer private gate; invitation/password identifies individual Assessment users. The proxy forwards only the GMF cookie and selected request headers, never Sites cookies or the platform service token. CORS is not enabled. Backend rejects direct requests without the server gateway key and validates Origin + custom header on mutations.

Do not publish a gateway configured to an invented/placeholder host. Current static publication fixes error text but does not yet provide backend connectivity. Activation requires the actual approved service URL.
