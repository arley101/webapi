#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Start the app
gunicorn -w 4 --bind=0.0.0.0:8000 app.main:app