#!/usr/bin/env zsh

# SYNOPSIS
#   Stops all AWIS stack background processes launched by start_awis.sh by matching process signatures.

closed=0

# Array of process signatures to target:
# - streamlit: the frontend
# - arq: the task worker
# - uvicorn: catches FastAPI (8000) and the 5 MCP servers (8001-8005)
patterns=(
    "streamlit run"
    "arq "
    "uvicorn.*800[0-5]"
)

for pattern in "${patterns[@]}"; do
    # pgrep checks if any process matches; pkill actually kills them
    if pgrep -f "$pattern" > /dev/null; then
        echo "\e[33mClosing processes matching: $pattern\e[0m"
        pkill -f "$pattern"
        ((closed++))
    fi
done

if [ $closed -eq 0 ]; then
    echo "\e[90mNo matching AWIS processes found running.\e[0m"
else
    echo "\e[32mClosed $closed AWIS process group(s).\e[0m"
fi