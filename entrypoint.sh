#!/bin/sh
set -e

# Fix permissions
chmod -R 755 ./bucket/prompts

# Start FastAPI server (foreground so container stays alive)
uvicorn app:app --host 0.0.0.0 --port 8000

echo "Starting server in 5 seconds..."

sleep 5