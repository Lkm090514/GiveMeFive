# V4.1 CI investigation — 2026-10-26

## Result and scope

The six original failures are caused by excluded runtime resources, not by an identified application-code defect. The GitHub source snapshot is incomplete for full Pathline execution. This change fixes CI orchestration and error reporting; it does **not** resolve the missing-resource release blocker or claim a green full regression.

Repository visibility was observed as public at investigation time. No visibility change, main update, force push or deployment is part of this change. No course content, PDF fragments, font binaries, private papers, student data or credentials are added.

## Original remote evidence

- Branch: `fix/v4.1-validation-20261026`
- Commit: `26c912944e4930321545c658be09504c5e9cf4b8`
- Latest failing run at start: <https://github.com/Lkm090514/GiveMeFive/actions/runs/40281010014>
- Job: `121434076799`; Ubuntu 24.04, Node 22.23.3, Python 3.13.16.
- Frontend: 70 tests, 64 pass, 6 fail. Backend and resource audit were skipped.
- Exact failing TAP blocks, including full error messages and stacks, are retained in [v41-failures-26c9129.txt](v41-failures-26c9129.txt).

| Test | Actual error / application-facing stack | Classification |
| --- | --- | --- |
| All course bundles resolve canonical IDs and image assets | `ENOENT: dist/data/topics/2026-10-21-378e0a8e6e/1.1.json`; `tests/integration.test.mjs:13:341` via `fs.readFileSync` | Missing excluded Topic bundles |
| Canonical course data and Assessment executable assets unchanged | `ENOENT: dist/data/reading-content.json`; `tests/integration.test.mjs:14:221` via `fs.readFileSync` | Missing excluded baseline course data; the hash assertion is never reached |
| real Unit download pauses, resumes only missing resources, detects corruption and retries failures | `Download incomplete: data/topics/.../1.1.json, assets/pages/...`; `transfer :19:1001` → `download :20:159` → `tests/offline-runtime.test.mjs:22:30` | File-backed test fetch returns 404 for excluded Topic JSON and page images |
| whole real course is complete by inventory, offline SW serves deep links and images, deletion is course scoped | Same `Download incomplete` resource list; `transfer :19:1001` → `download :20:159` → `tests/offline-runtime.test.mjs:33:51` | Same omissions across the full course |
| version inventories match every shipped byte and reject mixing releases | `ENOENT: dist/assets/pages/0047.webp`; `tests/offline-runtime.test.mjs:46:78` via `fs.readFileSync` | Excluded page assets; PDF.js CMaps/fonts and PDF fragments are also absent later in the inventory |
| PDF export reconstructs the real original file and does not mark browser offline content complete | `PDF verification failed: source/physics-range-0001.bin`; `downloadPDF :23:539` → `tests/offline-runtime.test.mjs:64:25` | Excluded original-PDF fragments return 404; the runtime correctly rejects them |

These errors reproduce on the local audit checkout. They are not evidence of Linux path-case issues, a broken mock implementation, dependency installation failure, or an Assessment answer-processing defect. The unchanged tests pass after the actual original assets are restored in an isolated local copy.

## Minimal change

`.github/workflows/v41-regression.yml` now runs three independent jobs:

1. The original `npm test`, unchanged, with Node 22.
2. All `python -m pytest -q tests`, with Python 3.13, including private question isolation and no-AI/unknown-answer tests.
3. Strict Pathline asset auditing. Missing assets retain a nonzero exit code. The prior `||` warning fallback is removed. A summary and complete JSON audit artifact are published even on audit failure.

There is no `continue-on-error`, no skipped/deleted tests, no relaxed assertion, and no fixture substitution. All business code and baseline hashes remain unchanged. A missing resource is still a failure, rather than an apparent pass. This also prevents a frontend failure from suppressing backend and resource evidence.

## Newly exposed backend failures and follow-up

The first independent run, <https://github.com/Lkm090514/GiveMeFive/actions/runs/40289661800>, ran all 79 backend tests under Python 3.13: 77 passed and two DOCX tests failed (`test_docx_answers_not_in_options` and `test_admin_many_papers_batch_reuses_queue_and_is_idempotent`). They assert that a DOCX import completes and that both PDF/DOCX files in a batch are imported. The previous workflow had never reached these tests.

`backend/bank.py` requires an external `soffice` or `libreoffice` executable for DOCX conversion; `pip install` alone does not provide it. The follow-up CI change probes for this dependency, logs whether it is absent, installs `libreoffice-writer` when needed, and prints its version before the unchanged backend suite runs. The two assertions now serialize the entire batch on failure instead of a truncated model repr; their pass/fail conditions remain identical. Actual job logs must confirm converter availability and the subsequent test outcome.

## Local verification

Local runtime: Node 24.22.1 / Python 3.12.14. GitHub's Node 22 / Python 3.13 execution must be checked separately.

| Check | Result |
| --- | --- |
| Original frontend tests on the clean GitHub source snapshot | 64 pass, 6 resource-related failures, 0 skips |
| Original frontend tests in an isolated copy, restoring original excluded assets without changing tests or application code | 70 pass, 0 failures, 0 skips |
| All backend tests on the clean GitHub source snapshot | 79 pass, 0 failures |
| `tests/test_private_library.py` and `tests/test_v41.py` | 9 pass; included within the 79 backend tests |
| Mind Flow reference core suites | 34 pass; included within the 70 frontend tests |
| Pathline runtime audit on clean source snapshot | 87/1,216 verified; 1,129 missing; no size/hash corruption observed |
| Pathline runtime audit in complete local copy | 1,216/1,216 verified; no failures |
| Patch whitespace | `git diff --check` passes |

The missing runtime inventory comprises 568 page images, 41 Topic bundles, 337 PDF fragments, 1 page-text JSON, 168 PDF.js CMaps and 14 standard-font files. Additional excluded baseline datasets are detected by the baseline test. `.gitignore` explicitly excludes these resource classes. Local restoration is verification only: these resources are not included in the commit or sent to Actions.

Backend output includes existing FastAPI shutdown-event and Starlette/httpx deprecation warnings; these do not fail the suite.

## Remaining acceptance and blocker

The clean remote checkout cannot pass the six original tests or full resource audit until it has an authorized, complete resource delivery mechanism. Repeating the same run cannot repair absent bytes. Do not remove tests, alter hashes, generate dummy textbook resources, or swallow audit failures to obtain a green badge.

Real browser E2E (navigation, persistent storage, refresh/recovery, offline service-worker behavior, PDF export), real complex/multipage PDF fidelity, and device-level iPad Safari acceptance have not been performed in this task. Python PDF fixtures and Node VM checks do not establish those results. Assessment's no-AI answer policy is unchanged.
