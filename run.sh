#!/bin/bash
set -e
cd "$(dirname "$0")"
PROFILE="${COMPOSE_PROFILE:-}"

if [ -n "$PROFILE" ]; then
    docker compose --profile "$PROFILE" run --rm extractor "$@"
else
    docker compose run --rm extractor "$@"
fi
