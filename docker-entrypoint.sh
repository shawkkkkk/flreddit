#!/bin/sh
set -eu

# Hosted volumes are commonly mounted as root. Prepare only the directory that
# contains Flreddit's database, then run the colony as its unprivileged user.
database_path="${FLREDDIT_DB:-/data/flreddit.sqlite3}"
state_directory=$(dirname "$database_path")

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$state_directory"
    chown -R flreddit:flreddit "$state_directory"
    exec gosu flreddit "$@"
fi

exec "$@"
