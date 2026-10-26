# GMF V4.1 — Private asset recovery and CI separation (2026-10-26)

## Input and verified local results

Source: user-supplied `GiveMeFive-AS-V4.1-Minimal-26275de.zip`. This file was available locally for this run; no new user upload was needed.

- Source manifest: 1,216 runtime resources (7 Units / 41 Topics).
- Created **private local** `dist/`-only archive from the manifest after verifying every expected byte count and SHA-256.
- Private archive SHA-256: `b2730a7f97a8bc5b7390fab5f17a042aa19bfe949387bb47a441b860b99dacdb`.
- Restore test using a **simulated sparse checkout** containing the manifest and 1 verified resource: 1,215 assets restored, 1 already valid, **1,216/1,216 rechecked**.
- Restore-script security tests: **5/5 passed** (round-trip/idempotency, same-size tampering, no overwrite of changed files, unexpected member rejection, invalid source refusing pack).
- Local Node test set after the earlier V4.1 cache mock patch: `node --test --test-concurrency=1 tests/*.test.mjs mf-stage-a-reference/tests/*.test.mjs` — **70/70 passed**. Parallel `npm test` had **intermittent offline-cache test failures** in this execution environment; CI now schedules files serially without dropping any tests.
- A local full Python test attempt in this run hit the available execution timeout after partial progress; **no new complete backend pass is claimed here**. Previous Work results were separately reported but not independently reproduced in this run.

## GitHub CI changes

- Private asset restoration is keyed by `GMF_COURSE_ASSETS_URL` (and optional read-only `GMF_COURSE_ASSETS_TOKEN`). The archive is downloaded into the ephemeral job only.
- The asset integrity gate remains strict and fails rather than manufacturing placeholders.
- Backend is split into full ordinary suite excluding only two DOCX cases and a **separate required** LibreOffice DOCX job for those exact two cases. A timeout/network failure is explicitly a failure, not a pass.
- CI uploads only the resource-audit JSON, not course content or the private archive.
- No production deployment, modification of `main`, repository visibility change, or upload of private resources occurred.

## Explicit remaining blockers

1. An **access-controlled** URL for the private asset archive and a GitHub Actions secret must still be provisioned. No GitHub CI green status is claimed.
2. The separately required DOCX job must complete on the remote runner. Giving installation more time is not itself evidence of success.
3. Real browser, complex PDF and iPad Safari acceptance are outstanding.
4. The source metadata contains a CC BY-NC-SA 4.0 notice; individual figure credits must be checked and commercial distribution needs rights review.

This document does **not** claim that the sparse GitHub checkout has already been repaired with those assets. The restore evidence comes from a local simulated sparse checkout.
