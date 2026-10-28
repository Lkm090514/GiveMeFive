# GiveMeFive V4.1 GitHub source import — 2026-10-26

## Provenance and scope

- Target: `Lkm090514/GiveMeFive`, private; branch `import/as-v4.1-26275de`.
- Inspected main/import branch before import: both `97aa278f9894be5cd8b5c78924c3271283787921`; only `.gitignore` tracked. No other branches after complete pagination. Write permission confirmed.
- Original ZIP: `GiveMeFive-AS-V4.1-Minimal-26275de.zip`, 159077338 bytes, 1643 entries/files, CRC test passed. SHA-256: `61b7e47a7ea5897a4f47a78f064cba8c6d11d7c67ca47095d279f3d8566dd220`.
- Archive records `26275de65b91fd8ff8219be7603915514f588bef`. No `.git` metadata. This import adds a new descendant of the existing remote commit; it does not recreate the absent development history or claim 26275de is a remote ancestor.
- Original ZIP and extracted source retained separately and unchanged in content. Test-generated caches are not archive entries.

## File completeness and exclusions

- 274 original archive files retained; 1369 original archive files excluded. Full exact paths, byte sizes, SHA-256 and reasons: `excluded-files.json`.
- Exclusions: 960 external textbook/page/topic/PDF-fragment files, 30 historical private exam review artifacts, 11 generated screenshots, 4 historical TAP outputs, and 364 PDF.js font/CMap binaries rejected by automatic approval review. The original ZIP preserves all excluded files; the prepared import tree omits them.
- `dist/` contains required editable vanilla JS/ES modules, not merely disposable build output. Fusion, Pathline (`dist/app.js`, `dist/pathline-core.js`), Mind Flow (`dist/mind-flow/`), Assessment V4.1 (`dist/assessment/v4/`), Python backend, SQL migrations, scripts and current tests are retained. Historical Assessment executable assets are retained because their full original source is absent from this Minimal archive.
- Keep course structure/metadata/manifests and PDF.js JavaScript/WASM runtime with existing notices. CMap and standard font binaries are excluded; restore them locally from the original ZIP before relying on PDF rendering, especially CJK text and non-embedded fonts. Textbook redistribution permissions/individual figure credits were not cleared, so embedded book content is excluded under the repository's existing exclusion policy. This is not a legal conclusion that the book cannot be redistributed under its own license.
- A plain clone does not include textbook pages, extracted textbook text/exercises, Topic payloads or PDF chunks. Pathline reading/offline course download/PDF export and six content-dependent Node tests need those external local resources restored at their original paths. They cannot be regenerated from this source-only checkout alone. Source-only clone is therefore not the complete runnable course distribution.
- Missing from the Minimal ZIP: original Git history, runtime/private databases and identities, private imported papers, historical `assessment-source`/`legacy-source`, V3 standalone tests/examples/licenses/development requirements. Do not interpret historical documentation as proof those directories are included. Current V4.1 source/backend can be developed; the historical React build cannot be reconstructed solely from this archive.

## Minimal import-only repairs

1. Preserve remote `.gitignore` safeguards, add last-launch and screenshot/private-review exclusions. Do not exclude all `dist/`.
2. Root `requirements-dev.txt` referenced absent `as-v3-reference/requirements-dev.txt`; point it to existing root `requirements.txt`, add pytest/reportlab and retain `python-docx==1.2.0`. This is a packaging repair, not a product change; no missing historical dependency lock is claimed to be recovered.
3. Restore `as-v3-reference/third_party/openassess-LICENSE.txt` from upstream LICENSE at pinned commit `35b5346895e390481aff47a1c37ff76a1be05b2b`; upstream Git blob `56b7b210f90c76be74e9e5765585db45d3aeee69`. Copy the archive's PDF.js Apache LICENSE to the second bundled PDF.js directory. Existing per-font/cmap/wasm notices preserved; the associated CMap/font binaries are now excluded after automatic review rejection.
4. Add this report, excluded-file manifest and tracked-file manifest. No application feature refactor; Assessment V4.1 formal flow remains non-AI.

## Verification

- Original archive: Node `npm test`: 70 passed / 0 failed.
- Sanitized source-only checkout before the subsequent PDF font/CMap binary exclusions: Node `npm test`: 64 passed / 6 failed because excluded course assets are unavailable. Failures: course bundles resolve; baseline content hashes; Unit download; full course offline inventory; shipped-byte inventory; original PDF export.
- Original archive Python tests: 71 passed / 4 failed. Same-type public/private matching exclusions and remaining-count expectations fail in `tests/test_v4.py` at lines 154, 178, 202, 285. These failures occur before sanitization; no functional fixes are included in this import.
- Sanitized source-only checkout before the subsequent PDF font/CMap binary exclusions, Python tests: 71 passed / 4 failed, exactly the same four matching/count regressions as the original archive.
- Entry smoke check: `/`, `/mind-flow/`, `/assessment/`, `/api/v4/health` all return HTTP 200 using the real Python app.
- `git diff --cached --check` reports pre-existing trailing whitespace/end-of-file blank lines in original code/vendor notices/synthetic PDFs. Preserved verbatim; not marked as a clean whitespace check.
- Python pinned production dependencies installed successfully in isolated environment; pytest and fixture tools installed for actual verification. The repaired development dependency entry is installable.
- No `build` script is declared. This project's runnable frontend is already in `dist/`; `content:build` is an external-content packaging step, not a frontend compiler. It requires excluded textbook input and was not run on the sanitized checkout. Missing historical React source prevents rebuilding its old compiled assets.
- Browser/iPad Safari, Windows launcher and real production deployment not tested in this import. No deployment or production database changes requested or performed.

## Git transfer and review

- CLI Git has no GitHub credentials in this environment; authenticated GitHub Git Data operations transfer audited blobs/tree/commit and update only the import ref, with expected-head check and force=false. Local Git index/diff/history and content-addressed hashes form the expected file tree. Verify final branch and commit through fresh remote reads after updating the ref; push success alone is insufficient.
- Preserve main and private visibility. No force push, branch deletion, merge, visibility change or production deployment.
- Recommendation: preserve this import branch for continued development. Before main merge, review exclusions/restore procedure and fix the four existing Python regressions. Do not treat this snapshot as release-ready.

## Resume checkpoint — 2026-10-26

- Recovered original local import commit `44e2f9b2466032fab77a0c868f203415e20fcf5b` and its unchanged original parent. This local commit remains preserved; it is not the final upload tree because it includes later-blocked font/CMap assets.
- Prepared final import contains 279 files: 274 original archive files plus five import/notice additions. It omits all 1369 excluded original files. The original ZIP and extracted source are preserved.
- Fresh GitHub reads confirm the repository is private and import/as-v4.1-26275de still points to 97aa278f9894be5cd8b5c78924c3271283787921. No import source commit has been attached to that branch.
- Attempt to create the remote tree was rejected by automatic approval review: the current user-authored request did not explicitly name/authorize this repository as the destination. No ref update, force push, merge or deployment was attempted. Explicit authorization naming the destination is needed before retrying remote writes.
- Earlier object uploads may exist as unreferenced Git objects. Their presence has not been fully enumerated; this checkpoint does not claim they constitute a completed push. Reuse safe existing objects by SHA when authorized, then verify the complete final tree and expected-head branch update.
- No repeated test suite was run in the resumed session: current changes are import exclusions and audit documentation. Earlier test results above are scoped to their actual tested file set and do not certify PDF rendering after font/CMap exclusions.
