#!/bin/sh
set -eu
umask 077
: "${GMF_PUBLIC_ORIGIN:?Set the private GMF HTTPS origin}"
: "${GMF_GATEWAY_KEY:?Set a server-only gateway secret on both hosts}"
: "${GMF_PERSISTENCE_CONFIRMED:?Confirm the persistent disk is mounted at /var/data}"
if [ "$GMF_PERSISTENCE_CONFIRMED" != 1 ] || [ ! -d /var/data ]; then echo 'Persistent disk is required' >&2; exit 1; fi
install -d -m 700 -o gmf -g gmf "$GMF_DATA_DIR"
exec gosu gmf uvicorn backend.app:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --no-access-log
