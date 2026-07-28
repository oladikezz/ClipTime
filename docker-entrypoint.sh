#!/usr/bin/env bash
set -euo pipefail

node /app/vendor/bgutil-ytdlp-pot-provider/server/build/main.js &
python /app/backend/server.py &

exec npm run start -- --host 0.0.0.0 --port "${PORT:-3000}"
