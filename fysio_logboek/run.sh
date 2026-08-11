#!/bin/sh
set -e
exec python -m uvicorn server:app --host 0.0.0.0 --port 8099 --no-access-log
