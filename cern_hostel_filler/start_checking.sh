#!/bin/bash

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

# Run the python script
screen -S "$SESSION_NAME" -p 0 -X stuff "python cern_hostel_filler.py$(printf \\r)"

echo "Done! You can attach to the session using: screen -r $SESSION_NAME"