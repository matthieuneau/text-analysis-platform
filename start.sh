#!/bin/bash

# tmux_start_services.sh
# Script to start all text analysis microservices in separate tmux windows

SESSION_NAME="text-analysis"

# Check if tmux session already exists
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "Session '$SESSION_NAME' already exists. Attaching..."
    tmux attach-session -t $SESSION_NAME
    exit 0
fi

# Create new tmux session (detached)
echo "Creating new tmux session: $SESSION_NAME"
tmux new-session -d -s $SESSION_NAME

# Rename the first window
tmux rename-window -t $SESSION_NAME:1 "gateway"

# Create additional windows
tmux new-window -t $SESSION_NAME:2 -n "preprocessing"
tmux new-window -t $SESSION_NAME:3 -n "sentiment"
tmux new-window -t $SESSION_NAME:4 -n "summarization"

# Send commands to each window
echo "Starting services..."

# Gateway (window 1)
tmux send-keys -t $SESSION_NAME:1 "cd ~/text-analysis-platform" C-m
tmux send-keys -t $SESSION_NAME:1 "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:1 "uvicorn services.gateway.app:app --host 0.0.0.0 --port 8000 --reload" C-m

# Preprocessing (window 2)
tmux send-keys -t $SESSION_NAME:2 "cd ~/text-analysis-platform" C-m
tmux send-keys -t $SESSION_NAME:2 "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:2 "uvicorn .app:app --host 0.0.0.0 --port 8001 --reload" C-m

# Sentiment Analysis (window 3)
tmux send-keys -t $SESSION_NAME:3 "cd ~/text-analysis-platform" C-m
tmux send-keys -t $SESSION_NAME:3 "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:3 "uvicorn .app:app --host 0.0.0.0 --port 8002 --reload" C-m

# Summarization (window 4)
tmux send-keys -t $SESSION_NAME:4 "cd ~/text-analysis-platform" C-m
tmux send-keys -t $SESSION_NAME:4 "source .venv/bin/activate" C-m
tmux send-keys -t $SESSION_NAME:4 "uvicorn services.summarization.app:app --host 0.0.0.0 --port 8003 --reload" C-m

# Switch to the gateway window (window 1)
tmux select-window -t $SESSION_NAME:1

echo "All services started in tmux session '$SESSION_NAME'"
echo "To attach to the session, run: tmux attach-session -t $SESSION_NAME"
echo ""
echo "Window layout:"
echo "  1: gateway        (port 8000)"
echo "  2: preprocessing  (port 8001)"
echo "  3: sentiment      (port 8002)"
echo "  4: summarization  (port 8003)"
echo ""
echo "Use Ctrl+b then 0-3 to switch between windows"
echo "Use Ctrl+b then d to detach from session"

# Attach to the session
tmux attach-session -t $SESSION_NAME
