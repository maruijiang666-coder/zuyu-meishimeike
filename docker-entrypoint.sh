#!/bin/sh
# Fix ownership of the mounted data directory, then drop privileges.
set -eu

DATA_PATH="${DATA_DIR:-/app/data}"

if [ "$(id -u)" = "0" ]; then
  mkdir -p "$DATA_PATH"
  chown -R appuser:appuser "$DATA_PATH"
  exec gosu appuser "$@"
fi

exec "$@"
