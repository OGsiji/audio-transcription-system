#!/bin/sh

echo "NODE_ENV is: $NODE_ENV"

if [ "$NODE_ENV" = "production" ]; then
    echo "Starting in production mode with New Relic monitoring..."
    exec newrelic-admin run-program python3 main.py
else
    echo "Starting without New Relic monitoring..."
    exec python3 main.py
fi