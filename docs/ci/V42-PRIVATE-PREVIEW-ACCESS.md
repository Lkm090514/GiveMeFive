# V4.2 private preview: fail-closed access gate (2026-10-27)

This document covers the **isolated managed QA preview adapter only**, not production student login, collaboration SSO, or a public launch.

## Risk found and resolved

The prior `scripts/managed-preview.py` returned the administrator preview cookie to **any visitor who POSTed `/qa-preview`**. Worse, backend `StaticFiles` serves the Pathline curriculum, images, and JSON without API authentication, so protecting only `/api/*` would not make the textbook private.

The adapter now:
- Refuses to start without `GMF_PREVIEW_PASSWORD` of at least 16 characters.
- Prompts for the password at `GET /qa-preview`, does not reflect the secret in HTML/logs, and denies incorrect POSTs.
- Gates **all** paths, including `/data/*`, `/content-runtime.js`, course images, and API routes.
- Sets a one-hour `HttpOnly; Secure; SameSite=Strict` cookie only after success.
- Sends `Cache-Control: private, no-store` for responses while gated.
- Keeps the preview's identity/database under `runtime/managed-preview`, separate from local/production data.
- Continues requiring `SITES_MANAGED_LINUX_CONTAINER=1`; it is not a substitute for the ordinary `npm start` / local launcher.

## Startup prerequisites

Use an **HTTPS-enabled restricted preview tunnel**. Provision a random, privately communicated password **via environment secret**, not in GitHub files, Actions logs, or a URL query. Start only in the actual managed-preview container:

```sh
SITES_MANAGED_LINUX_CONTAINER=1 GMF_PREVIEW_PASSWORD='[private password, 16+ chars]' \
  python scripts/managed-preview.py --host 127.0.0.1 --port 4173
```

The login cookie is Secure and intentionally will not authenticate over plain non-loopback HTTP. Do not disable Secure just to make a public HTTP deployment work.

Only a fully verified and legally distributable private curriculum archive should be restored into the **runtime container**. Never commit the 148 MB archive or personal student files to the public GitHub repository.

## Verification

Run `python -m pytest -q tests/test_managed_preview_gate.py`. The regression proves a non-logged-in client cannot fetch the app root, curriculum manifest, reading JSON, JS bundle, or API identity, verifies invalid passwords receive 403, and checks the cookie flags and successful post-login requests.

This gate is a **single-preview password**, not production-grade multi-user authorization, account recovery, rate limiting, cross-device synchronization, or identity separation. Its scope is one personal QA environment. Actual iPad Safari and a real HTTPS tunnel remain separate acceptance steps.
