# GMF V4.1 — private runtime assets for CI

**Status:** infrastructure prepared, **not** a completed release. This GitHub repository is public. No textbook PDF, page assets, private question papers, account data, or credentials may be committed here.

## Why the CI tests fail without this package

The public source snapshot has only a fraction of the 1,216 files enumerated by `dist/data/runtime-manifest.json`. The offline Pathline tests require exact original bytes and hashes. Replacing them with placeholders, mocking away the requirement, or relaxing tests is not acceptable.

The original user-supplied ZIP has been verified locally as 1,216/1,216 matching resources. Its `dist/data/source-metadata.json` identifies the source as **OpenStax University Physics Volume 1** with a **CC BY-NC-SA 4.0** notice and individual-figure credit conditions. **Do not assume redistribution on a commercial paid website is authorized.** Confirm the applicable permissions and maintain attribution before any public distribution.

## One-time private preparation on a trusted computer

Using the original complete V4.1 ZIP extracted to a trusted local directory:

```sh
python scripts/restore-course-assets.py pack --dist dist --archive private-gmf-course-assets.zip
```

The script checks every referenced file size and SHA-256 before packaging. It refuses missing, damaged, or modified assets and produces an archive containing **only** manifest-listed runtime paths under `dist/`. Do not upload the full original source ZIP to a file sharing service as a shortcut.

Keep the archive in **access-controlled private storage**. Configure either:

- GitHub repository **Actions secret** `GMF_COURSE_ASSETS_URL` with a secret HTTPS URL returning the ZIP; or
- `GMF_COURSE_ASSETS_URL` with a stable HTTPS resource endpoint **and**, when required, `GMF_COURSE_ASSETS_TOKEN` with a read-only bearer token.

Use least-privilege storage access; avoid publicly downloadable links. Never paste secrets or signed links into issues, pull requests, chat, logs, source files, or screenshots. Rotate any expiring URL. Access token requests do not follow redirects; point the URL directly at the resource.

GitHub UI: Settings → Secrets and variables → Actions → New repository secret. Because the repository is public, review collaborator permissions and protect workflow edits; secrets may be used by authorized branch workflows. Secrets are not provided to forked pull requests.

## CI behavior

- `frontend` downloads the private package into temporary runner storage, verifies/restores missing files, then executes `npm test`.
- `course-resources` separately verifies all 1,216 resources. It **remains a failing release gate** until all files match the manifest.
- `backend-core` runs all Python tests except two DOCX-specific cases. These **are not omitted from CI**: both are required in `backend-docx`.
- `backend-docx` installs LibreOffice and runs those two cases. The installation may still fail due to GitHub runner networking; such failure must be reported, not counted as passing.

Neither the course archive nor unpacked licensed resources are uploaded as public GitHub Action artifacts. The optional audit artifact contains file status metadata only.

## Validation scope and remaining blockers

Passing all automated jobs is necessary but not sufficient for release. Browser End-to-End checks, real complex PDF fidelity, iPad Safari testing, secure production identity, database backups, and course asset distribution rights remain separate gates.

Do not merge into `main` or deploy solely because these test jobs pass.
