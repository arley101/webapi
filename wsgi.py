# Azure App Service deployment configuration
# This file tells Azure how to run your Python application

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app

# This is required for Azure App Service
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
