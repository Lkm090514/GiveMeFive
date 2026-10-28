# GiveMeFive V4.3 — PUBLIC GitHub deployment contract (2026-10-28)

**Status: BLOCKED. This branch is not a ready-to-deploy public release.**

This repository intentionally does not contain licensed textbook/page resources,
the 196-page AP Physics C workbook, the 369-question private review database,
students' data, credentials or verified answer keys. A clean public checkout
must NOT start a visually complete but empty production website.

## What was actually fixed

- `Dockerfile.public` is a **full-site** image, unlike the API-only `Dockerfile`.
  It includes Pathline, Mind Flow, Assessment, PDF.js and FastAPI.
- The Docker image build verifies all **1,228** manifest-pinned resources,
  **7 Units / 41 nonempty Topics**, PDF.js fonts/CMaps/WASM. Missing content
  stops the build before an image can be published.
- `backend.public_app:create_app` serves frontend and backend on one HTTPS
  origin. The gateway secret is inserted server-side, never embedded in JS.
- The production factory and entrypoint require a persistent SQLite bank
  with **at least 369 published, source-authorized, human-reviewed questions**,
  with valid options, intact source images and verified answer keys.
  Unverified drafts, missing PDF assets or placeholder options block startup.
- GitHub Actions runs negative-gate tests. The full-site release job must
  remain **red** until authorized private resources are configured and pass.

## What is still missing

1. The original V4.3 GitHub tree tracks only 94/1,228 manifest resources.
   The remaining 1,134 are private. They have been recovered in an isolated
   archive, **not published to GitHub**.
2. The recovered 196-page workbook has 369 extracted *drafts*, **zero
   approved public questions and zero verified answer keys**. A passing
   import test is not a public question bank.
3. Rights to redistribute the workbook/questions/images have not been
   confirmed. Do not put private review databases, PDFs or page images into
   a public repository or public CI artifact.
4. No real HTTPS public deployment, real Safari verification, backup/restore
   drill or 41-topic visual QA has passed. The multi-course administrator
   specification is not implemented in full.

## Release procedure for the owner (only after rights and reviews)

1. Clone the reviewed branch, not the empty `main`.
2. Privately restore **authorized** textbook resources into `dist/` using
   `python scripts/restore-course-assets.py restore --dist dist --archive
   /secure/path/to/authorized-assets.zip` or the authenticated tree fetcher.
   Never commit these files or credentials to public GitHub.
3. Run `python scripts/verify-v43-deploy.py --dist dist --mode assets-only`.
   It must report 1,228/1,228 and 41/41, including PDF.js dependencies.
4. Complete **human review**, source redistribution permission checks and
   verified answer-key confirmation for all 369 workbook questions. Store
   reviewed production database and question images in an encrypted,
   operator-owned persistent volume at `/var/data/gmf/`.
5. Run `python scripts/verify-public-bank.py --db
   /var/data/gmf/modules.sqlite3 --data-root /var/data/gmf
   --min-published 369`. Any failure blocks release.
6. Run `npm test` and `python -m pytest tests -q`, then build
   `docker build -f Dockerfile.public -t gmf-v43-fullsite .`.
7. Configure TLS proxy, `GMF_PUBLIC_ORIGIN=https://<your-domain>`,
   `GMF_GATEWAY_KEY=<random-server-only-32+-chars>`,
   `GMF_PERSISTENCE_CONFIRMED=1`, a mounted persistent
   `/var/data`, and one worker. Never put secrets in public logs.
8. Start the container and verify `/api/v4/ready`, `/`,
   `/data/course.json`, all 41 topics, sampled PDF.js textbook pages,
   published bank APIs, login, upload, review, exam, submit, restart and
   backups on the actual HTTPS host. Check iPad Safari separately.
9. Only after these checks pass, approve the release PR and change the
   public default branch. Do not force-push or overwrite existing branches.

**Important:** This is a fail-closed deployment contract, not a guarantee
that any stranger can one-click deploy the licensed course material. The
owner must provide an authorized private resource channel and reviewed
public bank. Without them, refusing to deploy is the correct behavior.
