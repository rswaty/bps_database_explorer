#!/bin/bash
# Launch script for BPS Database Explorer

echo "Starting BPS Database Explorer..."
echo "The app will open in your default web browser."
echo "Press Ctrl+C to stop the server."
echo ""

# Activate virtual environment and run streamlit
source venv/bin/activate
streamlit run app.py
