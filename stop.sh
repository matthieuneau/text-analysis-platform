#!/bin/bash

# tmux_stop_services.sh
# Script to stop all text analysis microservices and kill the tmux session

SESSION_NAME="text-analysis"

# Check if session exists
if ! tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "Session '$SESSION_NAME' does not exist."
    exit 1
fi

echo "Stopping all services in session '$SESSION_NAME'..."

# Send Ctrl+C to all windows to stop the services
tmux send-keys -t $SESSION_NAME:1 C-c
tmux send-keys -t $SESSION_NAME:2 C-c
tmux send-keys -t $SESSION_NAME:3 C-c
tmux send-keys -t $SESSION_NAME:4 C-c

# Wait a moment for services to shut down gracefully
sleep 2

# Kill the entire session
tmux kill-session -t $SESSION_NAME

echo "All services stopped and session killed."
