#!/usr/bin/env bashio

bashio::log.info "🚀 Starting XiaoZhi Assistant..."

# Get Home Assistant token from supervisor
export SUPERVISOR_TOKEN=$(bashio::supervisor.token)

bashio::log.info "🔑 Supervisor token loaded"

# Start the application
cd /app && python3 main.py