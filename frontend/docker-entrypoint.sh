#!/bin/sh
# docker-entrypoint.sh — writes runtime env config into public/env.js before
# starting the Next.js server.  Variables default to localhost for local dev.

API_URL="${API_URL:-http://localhost:8000}"

cat > /app/public/env.js <<EOF
// Runtime environment configuration — generated at container start.
// Do NOT edit manually.
window.__ENV__ = {
  API_URL: "${API_URL}",
};
EOF

exec node server.js
