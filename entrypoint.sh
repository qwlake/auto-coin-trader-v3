#!/bin/bash
set -e

# Function to wait for database to be ready (if using external DB)
wait_for_db() {
    echo "Waiting for database to be ready..."
    # Add database connectivity check here if needed
    # For SQLite, this is not necessary
}

# Function to run database migrations
run_migrations() {
    echo "Running database migrations..."
    uv run python -c "
from database.connection import init_database
import asyncio
asyncio.run(init_database())
"
}

# Function to start the main trading application
start_main() {
    echo "Starting main trading application..."
    exec uv run python main.py
}

# Function to start the dashboard
start_dashboard() {
    echo "Starting Streamlit dashboard..."
    exec uv run streamlit run dashboard/main.py --server.port=8501 --server.address=0.0.0.0
}

# Main entrypoint logic
case "$1" in
    "main")
        wait_for_db
        run_migrations
        start_main
        ;;
    "dashboard")
        wait_for_db
        start_dashboard
        ;;
    "migrate")
        wait_for_db
        run_migrations
        ;;
    *)
        echo "Usage: $0 {main|dashboard|migrate}"
        echo "  main      - Start the trading application"
        echo "  dashboard - Start the Streamlit dashboard"
        echo "  migrate   - Run database migrations only"
        exit 1
        ;;
esac