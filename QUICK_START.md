# Quick Start Guide - BPS Database Explorer

## Step 1: Activate the Virtual Environment

The dependencies are already installed in a virtual environment. You need to activate it:

```bash
source venv/bin/activate
```

You'll know it's activated when you see `(venv)` at the start of your command prompt.

## Step 2: Run the App

### Option A: Using the launch script (easiest)
```bash
./run_app.sh
```

### Option B: Manual command
```bash
streamlit run app.py
```

## Step 3: Open in Browser

The app will automatically open in your default web browser at:
**http://localhost:8501**

If it doesn't open automatically, copy that URL into your browser.

## Step 4: Test the App

Try these features:

1. **Home Page**: View database statistics
2. **Model Search**: Search for "10080" or "Forest" to see models
3. **Modelers & Reviewers**: Enter model ID "10080_1_2_3_7" to see modelers
4. **Fire Frequency**: Enter model ID "10080_1_2_3_7" to see fire data
5. **Species Indicators**: Search for "Quercus" or "oak"
6. **Custom Query**: Try this query:
   ```sql
   SELECT bps_model_id, vegetation_type 
   FROM bps_models 
   LIMIT 10
   ```

## Stopping the App

Press `Ctrl+C` in the terminal where the app is running.

## Troubleshooting

- **If you get "command not found"**: Make sure you activated the virtual environment with `source venv/bin/activate`
- **If the browser doesn't open**: Manually go to http://localhost:8501
- **If port 8501 is busy**: Streamlit will automatically try the next available port (8502, 8503, etc.)
