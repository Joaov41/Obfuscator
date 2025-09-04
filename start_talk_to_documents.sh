#!/bin/bash
# Combined startup script for backend (with conda) and frontend
# for the "Talk to documents" application.

# --- Configuration ---
# Automatically detect the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR"

# Conda environment name for the backend
CONDA_ENV_NAME="redactor-backend"

# Ports configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000

# --- Color codes for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Functions ---
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

kill_port_process() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        print_warning "Found process(es) using port $port. Killing..."
        echo $pids | xargs kill -9 2>/dev/null
        sleep 1
        print_status "Port $port cleared"
    fi
}

# --- Startup ---
echo "========================================="
echo "  Talk to Documents - Application Startup"
echo "========================================="
echo ""
print_status "Project root: $PROJECT_ROOT"
echo ""

# --- Kill existing processes on required ports ---
echo "Checking for existing processes..."
kill_port_process $BACKEND_PORT
kill_port_process $FRONTEND_PORT
echo ""

# --- Environment Setup ---
echo "Setting up environment..."

# Try to find conda in common locations
CONDA_PATHS=(
    "/opt/anaconda3"
    "/opt/miniconda3"
    "$HOME/anaconda3"
    "$HOME/miniconda3"
    "/usr/local/anaconda3"
    "/usr/local/miniconda3"
    "$HOME/miniforge3"
    "/opt/homebrew/anaconda3"
)

CONDA_FOUND=false
for conda_path in "${CONDA_PATHS[@]}"; do
    if [ -f "$conda_path/etc/profile.d/conda.sh" ]; then
        source "$conda_path/etc/profile.d/conda.sh"
        CONDA_FOUND=true
        print_status "Conda sourced from $conda_path"
        break
    fi
done

if [ "$CONDA_FOUND" = false ]; then
    # Try to use conda if it's already in PATH
    if command -v conda &> /dev/null; then
        print_warning "Using conda from PATH"
    else
        print_error "Conda not found. Please install Anaconda/Miniconda or adjust the script."
        exit 1
    fi
fi

# Add Homebrew to PATH if it exists (for npm)
if [ -d "/opt/homebrew/bin" ]; then
    export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
    print_status "Homebrew added to PATH"
elif [ -d "/usr/local/bin" ]; then
    export PATH="/usr/local/bin:$PATH"
fi

# --- Validate Project Path ---
if [ ! -d "$PROJECT_ROOT" ]; then
    print_error "Project directory not found at $PROJECT_ROOT"
    exit 1
fi

if [ ! -d "$PROJECT_ROOT/backend" ]; then
    print_error "Backend directory not found at $PROJECT_ROOT/backend"
    exit 1
fi

if [ ! -d "$PROJECT_ROOT/frontend" ]; then
    print_error "Frontend directory not found at $PROJECT_ROOT/frontend"
    exit 1
fi

print_status "Project structure validated"
echo ""

# --- Start Backend ---
echo "Starting backend server..."
(
  cd "$PROJECT_ROOT/backend" || {
    print_error "Failed to navigate to backend directory"
    exit 1
  }
  
  # Check if conda environment exists
  if conda env list | grep -q "^$CONDA_ENV_NAME "; then
    conda activate "$CONDA_ENV_NAME" || {
      print_error "Failed to activate Conda environment '$CONDA_ENV_NAME'"
      exit 1
    }
    print_status "Activated Conda environment: $CONDA_ENV_NAME"
  else
    print_warning "Conda environment '$CONDA_ENV_NAME' not found"
    print_warning "Create it with: conda create -n $CONDA_ENV_NAME python=3.9"
    print_warning "Then: pip install -r $PROJECT_ROOT/backend/requirements.txt"
    print_warning "Attempting to continue with current Python environment..."
  fi
  
  print_status "Starting FastAPI backend on port $BACKEND_PORT..."
  python -m uvicorn main:app --reload --host 0.0.0.0 --port $BACKEND_PORT
) &
BACKEND_PID=$!
print_status "Backend server started with PID: $BACKEND_PID"

# Wait for backend to initialize
echo "Waiting for backend to initialize..."
sleep 3

# Check if backend is responding
if curl -s -o /dev/null -w "%{http_code}" http://localhost:$BACKEND_PORT/docs | grep -q "200"; then
    print_status "Backend is responding at http://localhost:$BACKEND_PORT"
else
    print_warning "Backend may not be fully initialized yet"
fi
echo ""

# --- Start Frontend ---
echo "Starting frontend development server..."
cd "$PROJECT_ROOT/frontend" || {
  print_error "Failed to navigate to frontend directory"
  kill $BACKEND_PID 2>/dev/null
  exit 1
}

# Check for npm
if ! command -v npm &> /dev/null; then
    print_error "npm not found. Please install Node.js and npm"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    print_warning "node_modules not found. Running npm install..."
    npm install || {
        print_error "npm install failed"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    }
fi

print_status "Starting React frontend on port $FRONTEND_PORT..."
echo ""
echo "========================================="
echo -e "${GREEN}Application starting...${NC}"
echo ""
echo "  Backend:  http://localhost:$BACKEND_PORT"
echo "  Frontend: http://localhost:$FRONTEND_PORT"
echo "  API Docs: http://localhost:$BACKEND_PORT/docs"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "========================================="
echo ""

# Set up trap to kill backend when frontend stops
trap "echo ''; print_warning 'Shutting down servers...'; kill $BACKEND_PID 2>/dev/null; exit" SIGINT SIGTERM

# Start frontend (this will run in foreground)
PORT=$FRONTEND_PORT npm start

# This line only executes if npm start exits normally
print_warning "Frontend server stopped. Cleaning up..."
kill $BACKEND_PID 2>/dev/null