# Identity and deployment boundary

The existing Fusion is browser-local. Its historical AS ChatGPT trusted-header helper is source only; no deployed auth/user table could be verified. V4 does not silently create a parallel account-registration service.

Local development reuses V3's token -> `{owner_id,role}` principal map. By default `scripts/run-v4.py` creates one random local-owner admin token in `runtime/v4/local-access.json` with mode 0600. The startup URL carries it in a fragment, the client immediately removes that fragment and exchanges it for an HttpOnly/SameSite Strict cookie. Use only on the local machine. Do not publish that development login URL.

Deployers may set `GMF_API_TOKENS` to a JSON object mapping independently generated secrets to principals (roles admin/student). Never use user-supplied `oai-authenticated-user-id` headers as proof of identity. The code deliberately rejects spoofed identity headers. Cookie mutations require the `X-GMF-Request: 1` same-origin header; no wildcard CORS is enabled. The student API uses a scoped V4 adapter over V3 exam_private imports. Only its owner can read an imported paper and associated sessions; only administrator imports can publish to the public bank.

Server sessions, responses, mistakes and custom paper definitions are isolated by owner_id in the SAME V3 SQLite database. Public questions are shared. Full source documents/layouts and arbitrary assets are admin-only; students get only approved answer-safe question/shared-stem crops or their own historical snapshots. Before exam submission, the session projection omits answer-key IDs, labels, explanations, records and grade data. An active exam blocks practice checking, mistake review and alternate session review.

Production requires a trusted authenticated reverse proxy or verified ChatGPT identity adapter, an explicit admin role source, TLS, durable Python hosting and backup/operations configuration. Those have NOT been deployed or verified in this task. Binding the development runner publicly or setting a browser-supplied identity header is not a supported production substitute.

The existing Sites project is static. Deploying its dist directory alone would omit the Python backend; therefore the previous HTTPS site is not overwritten with a nonfunctional V4 shell. `scripts/preview-v4.py` is supervised QA only: it enables fixture principals and a fixture-selection endpoint against `runtime/qa-preview`, entirely separate from normal `runtime/v4`. Never enable `GMF_QA_FIXTURE` in production.
