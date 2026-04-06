#!/bin/bash

# Change to the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Define the screen name
SESSION_NAME="cern_filler"

# 1. Kill the existing session if it exists
# We use 'quit' instead of 'kill' for a cleaner exit
echo "Stopping existing screen session: $SESSION_NAME..."
screen -S "$SESSION_NAME" -X quit 2>/dev/null

# Small delay to ensure the socket is released
sleep 1

# 2. Start a new detached screen session
echo "Starting new screen session: $SESSION_NAME..."
screen -dmS "$SESSION_NAME"

# 3. Send the commands to the new session
# We use 'stuff' to type the command and '\n' to press Enter
echo "Activating virtual environment and starting script..."

# Source the venv
screen -S "$SESSION_NAME" -p 0 -X stuff "source ../.venv/bin/activate$(printf \\r)"

# Run the python script in a restart loop so it auto-recovers from crashes
screen -S "$SESSION_NAME" -p 0 -X stuff "while true; do echo \"[\\$(date '+%Y-%m-%d %H:%M:%S')] Starting cern_hostel_filler.py...\"; python cern_hostel_filler.py; echo \"[\\$(date '+%Y-%m-%d %H:%M:%S')] Script exited (code \$?), restarting in 30s...\"; sleep 30; done$(printf \\r)"

echo "Done! You can attach to the session using: screen -r $SESSION_NAME"