# BPS Database Explorer

A web-based interface for exploring and querying the BPS (Biophysical Settings) database.

## Features

- 🔍 **Model Search**: Search models by Model ID, BPS Name, Vegetation Type, or keywords
- 📄 **Document Downloads**: Download Word documents directly from search results
- 🌲 **BPS Names**: View full Biophysical Setting names for each model
- 📊 **Quick Access**: Simple, intuitive interface - no database knowledge required

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

Start the Streamlit app:
```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

## Database Structure

The database contains the following main tables:

- **bps_models**: Main model information (901 models)
- **modelers**: Modeler information (734 modelers)
- **models**: Junction table linking models to modelers (2039 relationships)
- **bps_indicators**: Species indicators (5,788 records)
- **deterministic**: Deterministic transitions (3,035 records)
- **fire_frequency**: Fire frequency data (3,616 records)
- **probabilistic**: Probabilistic transitions (9,607 records)
- **ref_con_long**: Reference conditions long format (8,190 records)
- **ref_con_modified**: Reference conditions modified format (819 records)
- **scls_descriptions**: Succession class descriptions (3,035 records)

## Usage Examples

### Search for a Model
1. Enter a search term in the search box (e.g., "10080", "Oak Woodland", "Forest")
2. Browse results showing BPS Name, Model ID, Vegetation Type, and Map Zones
3. Click "Download Document" to get the Word file for any model

### Search Tips
- **By Model ID**: Search for "10080" or "10080_1_2_3_7"
- **By BPS Name**: Search for "Oak Woodland" or "Aspen Forest"
- **By Vegetation Type**: Search for "Forest" or "Woodland"
- **By Keywords**: Search for "oak", "fire", "mountain" to find related models

## Pre-built Queries

See `queries.py` for a collection of useful pre-built SQL queries that can be used in the Custom Query interface or imported in other scripts.

## Notes

- The Custom Query interface only allows SELECT queries for safety
- All queries are cached for performance
- Results can be downloaded as CSV files
