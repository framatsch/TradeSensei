#!/bin/sh
# docker-entrypoint.sh — sets API_URL for the Next.js proxy and
# starts the server.
#
# API_URL: backend URL reachable from within the cluster.
#   Default: http://localhost:8000 (for local dev without k8s)
#
# The Next.js reverse proxy (app/api/proxy/[...path]/route.ts) forwards all
# browser API requests to this URL — the backend is never exposed publicly.

export API_URL="${API_URL:-http://localhost:8000}"

exec node server.js
