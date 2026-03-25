#!/bin/sh
# docker-entrypoint.sh — sets INTERNAL_API_URL for the Next.js proxy and
# starts the server.
#
# INTERNAL_API_URL: backend URL reachable from within the cluster.
#   Default: http://localhost:8000 (for local dev without k8s)
#
# The Next.js reverse proxy (app/api/proxy/[...path]/route.ts) forwards all
# browser API requests to this URL — the backend is never exposed publicly.

export INTERNAL_API_URL="${INTERNAL_API_URL:-http://localhost:8000}"

exec node server.js
