#!/bin/sh
set -e

DATA_DIR="/home/appuser/.tradingagents"

# Ensure data directory exists and is owned by appuser
if [ -d "$DATA_DIR" ]; then
  chown -R appuser:appuser "$DATA_DIR" 2>/dev/null || true
fi

exec runuser -u appuser -w PATH -- "$@"
