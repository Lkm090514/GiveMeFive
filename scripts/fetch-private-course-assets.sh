#!/usr/bin/env bash
# Download access-controlled runtime assets into an ephemeral CI runner only.
set -euo pipefail
if [[ -z "${COURSE_ASSETS_URL:-}" ]]; then
  echo '::error::Missing GMF_COURSE_ASSETS_URL repository secret. Licensed course content is intentionally excluded from the public repository.'
  exit 1
fi
bundle="${RUNNER_TEMP:-/tmp}/gmf-private-course-assets.zip"
args=(--fail --silent --show-error --retry 3 --connect-timeout 30 --max-time 540 --proto '=https' --proto-redir '=https')
if [[ -n "${COURSE_ASSETS_TOKEN:-}" ]]; then
  # Never redirect a bearer-token request to another host.
  args+=(--header "Authorization: Bearer ${COURSE_ASSETS_TOKEN}")
else
  args+=(--location)
fi
curl "${args[@]}" "${COURSE_ASSETS_URL}" --output "$bundle"
python scripts/restore-course-assets.py restore --dist dist --archive "$bundle"
rm -f "$bundle"
