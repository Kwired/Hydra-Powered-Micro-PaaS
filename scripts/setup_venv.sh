#!/bin/bash

# Create a virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies based on OS
echo "Installing dependencies..."
pip install --upgrade pip

# Install project requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "Dependencies installed successfully."
else
    echo "Error: requirements.txt not found."
    exit 1
fi

echo "Virtual environment setup complete."
echo "To activate, run: source venv/bin/activate"
