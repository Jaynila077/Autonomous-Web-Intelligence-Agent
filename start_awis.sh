#!/bin/bash

# Cleanly shut down all background processes when Ctrl+C is pressed
trap 'kill 0' SIGINT

PROJECT_ROOT=$(pwd)
CONDA_ENV="awis"
MCP_PORTS=(8001 8002 8003 8004 8005)
MCP_TIMEOUT=30

echo "====================================================================="
echo " AWIS Autonomous Web Intelligence Agent - Startup Script (macOS/Zsh) "
echo "====================================================================="

# --- 1. Load .env file check ---
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "\033[32mFound .env file at project root.\033[0m"
else
    echo -e "\033[33mWarning: No .env file found at root. Ensure environment variables are configured.\033[0m"
fi

# --- Initialize and activate Conda ---
source ~/miniconda3/etc/profile.d/conda.sh
conda activate "$CONDA_ENV"

echo ""
echo -e "\033[36m[1/4] Starting AWIS MCP Tool Servers (5 microservices)...\033[0m"
python -m src.mcp_servers.run_all &

# --- 3. Wait for all 5 MCP servers to accept connections ---
echo -e "\033[33mWaiting for MCP servers to come online (up to $MCP_TIMEOUT seconds)...\033[0m"

end_time=$((SECONDS + MCP_TIMEOUT))
all_up=false

while [ $SECONDS -lt $end_time ]; do
    up_count=0
    for port in "${MCP_PORTS[@]}"; do
        # Use macOS netcat (nc) to scan for listening services
        if nc -z localhost "$port" 2>/dev/null; then
            ((up_count++))
        fi
    done
    
    if [ "$up_count" -eq "${#MCP_PORTS[@]}" ]; then
        all_up=true
        break
    fi
    sleep 1
done

if [ "$all_up" = true ]; then
    echo -e "\033[32mAll 5 MCP servers are up.\033[0m"
else
    echo -e "\033[33mWarning: Not all MCP servers came online within $MCP_TIMEOUT seconds.\033[0m"
    echo -e "\033[33mFastAPI or arq may fail to start if MOCK_AGENT is set to false.\033[0m"
fi

echo ""
echo -e "\033[36m[2/4] Starting FastAPI Server (Port 8000)...\033[0m"
uvicorn src.api.main:app --reload --port 8000 &

echo -e "\033[36m[3/4] Starting ARQ Task Worker...\033[0m"
python -m arq src.api.arq_worker.WorkerSettings &

echo -e "\033[36m[4/4] Starting Frontend UI...\033[0m"
streamlit run src/ui/app.py &

echo ""
echo -e "\033[32mAll services launched in the background. Press Ctrl+C to terminate everything.\033[0m"

# Keep script running to hold the terminal open
wait