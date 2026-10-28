#!/bin/sh
set -eu
umask 077
: "${GMF_PUBLIC_ORIGIN:?Set public HTTPS origin}"
: "${GMF_GATEWAY_KEY:?Set server-only random 32+ character secret}"
: "${GMF_PERSISTENCE_CONFIRMED:?Persistent disk must be confirmed}"
if [ "${GMF_PERSISTENCE_CONFIRMED}" != 1 ] || [ ! -d /var/data ]; then
  echo "BLOCKED: persistent /var/data disk is required" >&2
  exit 2
fi
if [ ! -f "${GMF_DATA_DIR:-/var/data/gmf}/modules.sqlite3" ]; then
  echo "BLOCKED: reviewed public question bank database is missing" >&2
  exit 2
fi
# Do not generate a new empty database during startup.
python scripts/verify-v43-deploy.py --dist dist --mode assets-only
python scripts/verify-public-bank.py --db "${GMF_DATA_DIR:-/var/data/gmf}/modules.sqlite3" \
  --data-root "${GMF_DATA_DIR:-/var/data/gmf}" --min-published "${GMF_MIN_PUBLISHED:-369}"
exec gosu gmf uvicorn backend.public_app:create_app --factory \
  --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --no-access-log \
  --proxy-headers --forwarded-allow-ips "${GMF_TRUSTED_PROXY_IPS:-127.0.0.1}"
