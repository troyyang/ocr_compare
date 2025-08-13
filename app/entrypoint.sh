#!/bin/bash
set -e

# Set default environment variables
export PYTHONPATH="/app:${PYTHONPATH:-}"

# Debug information
echo "Current PATH: $PATH"
echo "Current VIRTUAL_ENV: $VIRTUAL_ENV"

# Activate virtual environment if it exists
if [ -f "/app/.venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source /app/.venv/bin/activate
    echo "Virtual environment activated"
    echo "Python location: $(which python)"
    echo "Pip location: $(which pip)"
else
    echo "Warning: Virtual environment not found at /app/.venv"
    echo "Trying to proceed with system Python..."
fi

# Validate Python and pip versions
echo "Python version: $(python --version 2>&1 || echo 'Python not found')"
echo "Pip version: $(pip --version 2>&1 || echo 'Pip not found')"

# Install any additional requirements if needed
if [ -f "/app/requirements.txt" ]; then
    echo "Installing additional requirements..."
    pip install --no-cache-dir -r /app/requirements.txt
fi

# Run the command passed to the entrypoint
echo "Executing command: $@"
exec "$@"
