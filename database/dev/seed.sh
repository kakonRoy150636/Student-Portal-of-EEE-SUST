#!/bin/sh
set -eu

if [ "${ENVIRONMENT:-}" != "development" ]; then
    echo "Development seed refused: ENVIRONMENT must be development." >&2
    exit 1
fi

exec psql --no-psqlrc --set=ON_ERROR_STOP=1 --single-transaction --file=/seed/seed.sql
