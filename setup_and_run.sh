#!/bin/bash
# Simple setup and run script for colleagues

echo "=========================================="
echo "BPS Database Explorer - Setup"
echo "=========================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    echo "Please install Python 3 and try again."
    exit 1
fi

echo "✓ Python 3 found"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Check if database exists
if [ ! -f "bps_database.db" ]; then
    echo "⚠️  Warning: bps_database.db not found!"
    echo "Please make sure the database file is in this directory."
    exit 1
fi

echo "✓ Database file found"
echo ""
echo "=========================================="
echo "Starting BPS Database Explorer..."
echo "=========================================="
echo ""
echo "The app will open in your web browser."
echo "If it doesn't, go to: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server."
echo ""

# Run the app
streamlit run app.py
