#!/bin/bash
# Startup script for Azure App Service

echo "Starting EliteDynamicsAPI..."
echo "Python version:"
python --version

echo "Checking if uvicorn is available..."
python -c "import uvicorn; print('uvicorn imported successfully')" || exit 1

echo "Starting application with uvicorn directly..."
cd /home/site/wwwroot
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000