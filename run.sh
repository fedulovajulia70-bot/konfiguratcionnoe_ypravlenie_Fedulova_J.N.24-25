#!/bin/sh
cd "$(dirname "$0")" || exit 1
exec "${PYTHON:-python3}" src/main.py "$@"
