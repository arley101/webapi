#!/bin/bash
echo "Starting EliteDynamicsAPI..."

# Install dependencies with timeout and progress
echo "Installing dependencies..."
pip install --no-cache-dir --disable-pip-version-check -r requirements.txt &
INSTALL_PID=$!

# Show progress while installing
while kill -0 $INSTALL_PID 2>/dev/null; do
    echo "Installing packages..."
    sleep 10
done

wait $INSTALL_PID
INSTALL_EXIT_CODE=$?

if [ $INSTALL_EXIT_CODE -ne 0 ]; then
    echo "Package installation failed with exit code $INSTALL_EXIT_CODE"
    exit 1
fi

echo "Dependencies installed successfully. Starting application..."

# Start gunicorn with faster startup options
exec gunicorn -w 1 --bind=0.0.0.0:8000 --timeout 30 --preload app.main:app