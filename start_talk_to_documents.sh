#!/bin/bash
# Combined startup script for backend (with conda) and frontend
# for the "Talk to documents" application.

# --- Configuration ---
# Project directory name
PROJECT_DIR_NAME="Talk to documents"
# Assumed location of the project directory
BASE_PROJECT_PATH="$HOME/Documents" # $HOME usually expands to /Users/your_username
# Full path to the project root
PROJECT_ROOT="$BASE_PROJECT_PATH/$PROJECT_DIR_NAME"

# Conda environment name for the backend
CONDA_ENV_NAME="redactor-backend" # Keep this if it's your existing backend env

# --- Environment Setup ---
echo "Setting up environment..."

# Source Conda
CONDA_BASE_DIR="/opt/anaconda3" # Or your specific Anaconda/Miniconda installation path
if [ -f "$CONDA_BASE_DIR/etc/profile.d/conda.sh" ]; then
    source "$CONDA_BASE_DIR/etc/profile.d/conda.sh"
    echo "Conda sourced from $CONDA_BASE_DIR."
else
    echo "ERROR: conda.sh not found at $CONDA_BASE_DIR/etc/profile.d/conda.sh. Please check CONDA_BASE_DIR." >&2
    exit 1
fi

# Add Homebrew (and npm) to PATH if it exists
HOMEBREW_PREFIX="/opt/homebrew" # Common for Apple Silicon Macs
if [ -d "$HOMEBREW_PREFIX/bin" ]; then
    export PATH="$HOMEBREW_PREFIX/bin:$HOMEBREW_PREFIX/sbin:$PATH"
    echo "Homebrew added to PATH from $HOMEBREW_PREFIX."
else
    echo "INFO: Homebrew directory $HOMEBREW_PREFIX/bin not found. Assuming npm is in PATH."
fi

# --- Validate Project Path ---
if [ ! -d "$PROJECT_ROOT" ]; then
    echo "ERROR: Project directory not found at $PROJECT_ROOT" >&2
    echo "Please ensure the folder '$PROJECT_DIR_NAME' exists in '$BASE_PROJECT_PATH'." >&2
    exit 1
fi
echo "Project root identified as: $PROJECT_ROOT"

# --- Start Backend ---
echo "Starting backend server..."
(
  cd "$PROJECT_ROOT/backend" || {
    echo "ERROR: Failed to navigate to backend directory: $PROJECT_ROOT/backend" >&2
    exit 1 # Exit subshell
  }
  echo "Current directory for backend: $(pwd)"

  # Activate Conda environment
  conda activate "$CONDA_ENV_NAME" || {
    echo "ERROR: Failed to activate Conda environment '$CONDA_ENV_NAME'." >&2
    echo "Please ensure the environment exists. You can create it with:" >&2
    echo "conda create -n $CONDA_ENV_NAME python=3.9 # Or your desired Python version" >&2
    echo "Then, navigate to $PROJECT_ROOT/backend and run: pip install -r requirements.txt" >&2
    exit 1 # Exit subshell
  }
  echo "Successfully activated Conda environment: $CONDA_DEFAULT_ENV"
  
  echo "Starting Uvicorn server for FastAPI backend..."
  # Ensure PyMuPDF (fitz) and other dependencies are installed in this environment
  python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
) &
BACKEND_PID=$!
echo "Backend server started with PID: $BACKEND_PID"
# Wait a few seconds for the backend to initialize
sleep 5

# --- Start Frontend ---
echo "Starting frontend development server..."
cd "$PROJECT_ROOT/frontend" || {
  echo "ERROR: Failed to navigate to frontend directory: $PROJECT_ROOT/frontend" >&2
  # Optionally kill the backend if frontend fails to start
  # kill $BACKEND_PID
  exit 1
}
echo "Current directory for frontend: $(pwd)"

# Check for npm
if ! command -v npm &> /dev/null; then
    echo "ERROR: npm could not be found. Please ensure Node.js and npm are installed and in your PATH." >&2
    # kill $BACKEND_PID
    exit 1
fi

echo "Starting npm development server for React frontend..."
# This will typically open the app in a browser.
# If it doesn't, you might need to manually open http://localhost:3000 (or whatever port it uses)
npm start

# --- Cleanup (Optional) ---
# This part is tricky because npm start usually runs in the foreground and keeps the script alive.
# If you want to kill the backend when you stop the frontend (e.g., with Ctrl+C),
# you might need a more complex trap mechanism.
# For now, this script will exit when npm start is terminated. The backend will continue running in the background.
# You would typically stop the backend manually using its PID or by closing the terminal if not detached.

# To ensure backend is killed when script exits (e.g. on Ctrl+C of npm start)
# trap "echo 'Stopping backend server...'; kill $BACKEND_PID; exit" SIGINT SIGTERM
# echo "Frontend server started. Press Ctrl+C to stop both frontend and (if trap is enabled) backend."
# wait $BACKEND_PID # This would make the script wait for the backend if npm start was also backgrounded.
# Since npm start is foreground, the script effectively waits for it.

echo "Script finished. If npm start was exited, the backend server (PID: $BACKEND_PID) might still be running." 