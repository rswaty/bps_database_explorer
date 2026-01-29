import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import os
import re
import altair as alt
import zipfile
import io
# Updated: 2026-01-28 - Removed succession table, added ref_percent, removed species italics
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Page configuration
st.set_page_config(
    page_title="Biophysical Settings (BPS) Information Explorer",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database connection
DB_PATH = Path(__file__).parent / "bps_database.db"
DOCS_PATH = Path(__file__).parent / "all_bps_docs"

# Check if database exists
if not DB_PATH.exists():
    st.error(f"❌ Database file not found at: {DB_PATH}")
    st.error("Please make sure bps_database.db is in the repository.")
    st.stop()

@st.cache_resource
def get_connection():
    """Create and cache database connection - thread-safe for Streamlit"""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found: {DB_PATH}")
    # Use check_same_thread=False to allow connections across Streamlit threads
    # This is safe for read-only operations
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)

@st.cache_data
def run_query(query, params=None):
    """Execute a query and return results as DataFrame"""
    # Create a new connection for each query to avoid thread issues
    # This is safe because SQLite handles concurrent reads well
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    try:
        if params:
            df = pd.read_sql_query(query, conn, params=params)
        else:
            df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()

@st.cache_data
def get_vegetation_types():
    """Get list of unique vegetation types - cleaned to remove map zone data"""
    query = "SELECT DISTINCT vegetation_type FROM bps_models WHERE vegetation_type IS NOT NULL ORDER BY vegetation_type"
    df = run_query(query)
    
    # Clean vegetation types - extract only the text before newlines or "Map Zone"
    cleaned_types = set()
    for veg_type in df['vegetation_type'].dropna():
        if veg_type:
            # Split by newline and take first part, or split by "Map Zone" and take first part
            cleaned = str(veg_type).split('\n')[0].split('Map Zone')[0].strip()
            if cleaned:
                cleaned_types.add(cleaned)
    
    # Sort and return
    sorted_types = sorted(list(cleaned_types))
    return ['All'] + sorted_types

@st.cache_data
def get_unique_map_zones():
    """Get list of unique map zone numbers"""
    query = """
    SELECT DISTINCT map_zones 
    FROM bps_models 
    WHERE map_zones IS NOT NULL 
    ORDER BY map_zones
    """
    df = run_query(query)
    # Extract individual zone numbers from comma-separated values
    zones = set()
    for zone_str in df['map_zones'].dropna():
        if zone_str:
            # Split by comma and extract numbers
            parts = str(zone_str).split(',')
            for part in parts:
                try:
                    zones.add(int(part.strip()))
                except:
                    pass
    return sorted(list(zones))

@st.cache_data
def get_fire_frequency_ranges():
    """Get min/max return intervals for each severity category"""
    query = """
    SELECT 
        severity,
        MIN("return_interval(years)") as min_val,
        MAX("return_interval(years)") as max_val
    FROM fire_frequency
    WHERE severity IS NOT NULL
    GROUP BY severity
    """
    df = run_query(query)
    ranges = {}
    for _, row in df.iterrows():
        if pd.notna(row['min_val']) and pd.notna(row['max_val']):
            ranges[row['severity']] = {
                'min': int(row['min_val']),
                'max': int(row['max_val'])
            }
    return ranges

def get_species_list_for_model(model_id):
    """Get list of scientific names for a model from the species table"""
    species_query = """
    SELECT DISTINCT scientific_name
    FROM bps_indicators
    WHERE bps_model_id = ?
    AND scientific_name IS NOT NULL
    ORDER BY scientific_name
    """
    try:
        species_df = run_query(species_query, params=(model_id,))
        return species_df['scientific_name'].dropna().astype(str).tolist()
    except:
        return []

def italicize_scientific_names_from_table(text, species_list):
    """
    Italicize scientific names in text by matching against species list from database.
    Handles full names and abbreviations (e.g., "Q. garryana" for "Quercus garryana").
    Also handles subspecies variations (subsp./ssp./subspecies).
    """
    if not text or pd.isna(text) or not species_list:
        return text
    
    text = str(text)
    
    # Process each species name
    for scientific_name in species_list:
        if not scientific_name or len(scientific_name.strip()) < 3:
            continue
        
        scientific_name = scientific_name.strip()
        
        # Split into genus and species parts
        parts = scientific_name.split()
        if len(parts) < 2:
            continue
        
        genus = parts[0]
        species = parts[1]
        genus_first_letter = genus[0] if genus else ""
        
        # Handle subspecies variations
        # Check if there's a subspecies part (e.g., "Festuca idahoensis subsp. roemeri")
        subspecies_part = None
        if len(parts) >= 4 and parts[2].lower() in ['subsp.', 'ssp.', 'subspecies', 'var.', 'variety']:
            subspecies_part = parts[3] if len(parts) > 3 else None
        elif len(parts) >= 3:
            # Sometimes subspecies is written as "species subsp. name" or "species ssp. name"
            if parts[1].lower() not in ['subsp.', 'ssp.', 'subspecies', 'var.', 'variety']:
                # No subspecies indicator, just genus species
                pass
        
        # Create patterns to match:
        # 1. Full name: "Quercus garryana" or "Festuca idahoensis subsp. roemeri"
        # 2. Abbreviated genus: "Q. garryana" or "F. idahoensis subsp. roemeri"
        # Use word boundaries to avoid partial matches
        
        # Base patterns (genus species) - always include these
        base_patterns = [
            (rf'\b{re.escape(scientific_name)}\b', scientific_name),  # Full name exactly
            (rf'\b{re.escape(genus)}\s+{re.escape(species)}\b', f"{genus} {species}"),  # Genus species (even if DB has subspecies)
            (rf'\b{re.escape(genus_first_letter)}\.\s+{re.escape(species)}\b', f"{genus_first_letter}. {species}"),  # Q. garryana
            (rf'\b{re.escape(genus_first_letter)}\s+{re.escape(species)}\b', f"{genus_first_letter} {species}"),  # Q garryana (no period)
        ]
        
        # If there's a subspecies, also create patterns for it
        if subspecies_part:
            # Match "genus species subsp. subspecies" or "genus species ssp. subspecies"
            # Also handle cases where text has spaces in subspecies name (e.g., "r oemeri" vs "roemeri")
            subsp_patterns = [
                (rf'\b{re.escape(genus)}\s+{re.escape(species)}\s+subsp\.\s+{re.escape(subspecies_part)}\b', f"{genus} {species} subsp. {subspecies_part}"),
                (rf'\b{re.escape(genus)}\s+{re.escape(species)}\s+ssp\.\s+{re.escape(subspecies_part)}\b', f"{genus} {species} ssp. {subspecies_part}"),
                (rf'\b{re.escape(genus_first_letter)}\.\s+{re.escape(species)}\s+subsp\.\s+{re.escape(subspecies_part)}\b', f"{genus_first_letter}. {species} subsp. {subspecies_part}"),
                (rf'\b{re.escape(genus_first_letter)}\.\s+{re.escape(species)}\s+ssp\.\s+{re.escape(subspecies_part)}\b', f"{genus_first_letter}. {species} ssp. {subspecies_part}"),
                # Handle spaced subspecies names (e.g., "ssp. r oemeri" -> "ssp. roemeri")
                (rf'\b{re.escape(genus)}\s+{re.escape(species)}\s+ssp\.\s+{subspecies_part[0]}\s+{subspecies_part[1:]}\b', f"{genus} {species} ssp. {subspecies_part}"),
            ]
            base_patterns.extend(subsp_patterns)
        
        # Replace each pattern with italicized version (markdown format)
        # Process in reverse order (longest first) to avoid partial matches
        for pattern, replacement in reversed(base_patterns):
            # Only replace if not already italicized
            if f"*{replacement}*" not in text and f"<i>{replacement}</i>" not in text:
                text = re.sub(pattern, f"*{replacement}*", text, flags=re.IGNORECASE)
    
    return text

def italicize_scientific_names_from_table_html(text, species_list):
    """
    Italicize scientific names in text for HTML/PDF format.
    Same as italicize_scientific_names_from_table but uses HTML <i> tags.
    Also handles subspecies variations (subsp./ssp./subspecies).
    """
    if not text or pd.isna(text) or not species_list:
        return text
    
    text = str(text)
    
    # Process each species name
    for scientific_name in species_list:
        if not scientific_name or len(scientific_name.strip()) < 3:
            continue
        
        scientific_name = scientific_name.strip()
        
        # Split into genus and species parts
        parts = scientific_name.split()
        if len(parts) < 2:
            continue
        
        genus = parts[0]
        species = parts[1]
        genus_first_letter = genus[0] if genus else ""
        
        # Handle subspecies variations
        # Check if there's a subspecies part (e.g., "Festuca idahoensis subsp. roemeri")
        subspecies_part = None
        if len(parts) >= 4 and parts[2].lower() in ['subsp.', 'ssp.', 'subspecies', 'var.', 'variety']:
            subspecies_part = parts[3] if len(parts) > 3 else None
        
        # Create patterns to match - always include genus+species even if DB has subspecies
        base_patterns = [
            (rf'\b{re.escape(scientific_name)}\b', scientific_name),  # Full name exactly
            (rf'\b{re.escape(genus)}\s+{re.escape(species)}\b', f"{genus} {species}"),  # Genus species (even if DB has subspecies)
            (rf'\b{re.escape(genus_first_letter)}\.\s+{re.escape(species)}\b', f"{genus_first_letter}. {species}"),  # Q. garryana
            (rf'\b{re.escape(genus_first_letter)}\s+{re.escape(species)}\b', f"{genus_first_letter} {species}"),  # Q garryana (no period)
        ]
        
        # If there's a subspecies, also create patterns for it
        if subspecies_part:
            # Match "genus species subsp. subspecies" or "genus species ssp. subspecies"
            # Also handle cases where text has spaces in subspecies name (e.g., "r oemeri" vs "roemeri")
            subsp_patterns = [
                (rf'\b{re.escape(genus)}\s+{re.escape(species)}\s+subsp\.\s+{re.escape(subspecies_part)}\b', f"{genus} {species} subsp. {subspecies_part}"),
                (rf'\b{re.escape(genus)}\s+{re.escape(species)}\s+ssp\.\s+{re.escape(subspecies_part)}\b', f"{genus} {species} ssp. {subspecies_part}"),
                (rf'\b{re.escape(genus_first_letter)}\.\s+{re.escape(species)}\s+subsp\.\s+{re.escape(subspecies_part)}\b', f"{genus_first_letter}. {species} subsp. {subspecies_part}"),
                (rf'\b{re.escape(genus_first_letter)}\.\s+{re.escape(species)}\s+ssp\.\s+{re.escape(subspecies_part)}\b', f"{genus_first_letter}. {species} ssp. {subspecies_part}"),
                # Handle spaced subspecies names (e.g., "ssp. r oemeri" -> "ssp. roemeri")
                (rf'\b{re.escape(genus)}\s+{re.escape(species)}\s+ssp\.\s+{subspecies_part[0]}\s+{subspecies_part[1:]}\b', f"{genus} {species} ssp. {subspecies_part}"),
            ]
            base_patterns.extend(subsp_patterns)
        
        # Replace each pattern with italicized version (HTML format)
        # Process in reverse order (longest first) to avoid partial matches
        for pattern, replacement in reversed(base_patterns):
            # Only replace if not already italicized
            if f"<i>{replacement}</i>" not in text and f"*{replacement}*" not in text:
                text = re.sub(pattern, f"<i>{replacement}</i>", text, flags=re.IGNORECASE)
    
    return text

# Main title
st.title("🌲 Biophysical Settings (BPS; historical ecosystems) Information Explorer")

# Header section with logos and background information placeholder
col_logo_left, col_info, col_logo_right = st.columns([1, 2, 1])

with col_logo_left:
    st.markdown("### Logo Placeholder")
    st.info("📷 **Left Logo**\n\nAdd your organization logo here")
    # Placeholder for logo upload/display
    # st.image("path/to/logo_left.png", use_container_width=True)

with col_info:
    st.markdown("### Background Information")
    st.info("📝 **Background Information**\n\nAdd background information about Biophysical Settings (BPS) and historical ecosystems here. This section can include:\n- Overview of BPS concepts\n- How to use this explorer\n- Data sources and methodology\n- Contact information")
    # Placeholder for background text
    # st.markdown("""
    # **About Biophysical Settings (BPS)**
    # 
    # Biophysical Settings represent historical ecosystems...
    # """)

with col_logo_right:
    st.markdown("### Logo Placeholder")
    st.info("📷 **Right Logo**\n\nAdd your organization logo here")
    # Placeholder for logo upload/display
    # st.image("path/to/logo_right.png", use_container_width=True)

st.markdown("---")

# Get filter options
vegetation_types = get_vegetation_types()
map_zones_list = get_unique_map_zones()
fire_ranges = get_fire_frequency_ranges()

# Create filter sidebar
with st.sidebar:
    st.header("📤 Upload CSV File")
    st.caption('.csv file should have one column named "bps_model_id", and cells below should have values such as "10880_12_13_14_25"')
    
    # CSV file upload
    uploaded_file = st.file_uploader(
        "Choose CSV file",
        type=['csv'],
        help="Upload a CSV file containing bps_model_id values. The file can have a column named 'bps_model_id', 'model_id', 'BPS_Model_ID', or the first column will be used."
    )
    
    # Process uploaded CSV
    csv_model_ids = []
    csv_not_found = []
    
    # Initialize csv_not_found in session state for later use
    if 'csv_not_found' not in st.session_state:
        st.session_state.csv_not_found = []
    
    if uploaded_file is not None:
        try:
            # Read CSV
            csv_df = pd.read_csv(uploaded_file)
            
            # Try to find bps_model_id column (case-insensitive, handle variations)
            id_column = None
            possible_names = ['bps_model_id', 'model_id', 'bps_modelid', 'modelid', 'BPS_Model_ID', 'Model_ID']
            
            for col in csv_df.columns:
                if col.lower().strip() in [name.lower() for name in possible_names]:
                    id_column = col
                    break
            
            # If not found, use first column
            if id_column is None:
                id_column = csv_df.columns[0]
                st.info(f"ℹ️ Using first column '{id_column}' as model IDs")
            
            # Extract model IDs, remove duplicates and empty values
            csv_model_ids = csv_df[id_column].dropna().astype(str).str.strip().unique().tolist()
            csv_model_ids = [mid for mid in csv_model_ids if mid]  # Remove empty strings
            
            if csv_model_ids:
                st.success(f"✅ Found {len(csv_model_ids)} model ID(s) in CSV")
                
                # Check which ones exist in database
                if len(csv_model_ids) > 0:
                    # Query to check which IDs exist
                    placeholders = ','.join(['?'] * len(csv_model_ids))
                    check_query = f"""
                    SELECT bps_model_id 
                    FROM bps_models 
                    WHERE bps_model_id IN ({placeholders})
                    """
                    existing_df = run_query(check_query, params=tuple(csv_model_ids))
                    existing_ids = set(existing_df['bps_model_id'].astype(str).tolist())
                    csv_not_found = [mid for mid in csv_model_ids if mid not in existing_ids]
                    st.session_state.csv_not_found = csv_not_found  # Store for later use
                    
                    found_count = len(existing_ids)
                    if csv_not_found:
                        st.warning(f"⚠️ {len(csv_not_found)} model ID(s) not found in database")
                        with st.expander("Show IDs not found"):
                            st.write(", ".join(csv_not_found[:20]))  # Show first 20
                            if len(csv_not_found) > 20:
                                st.caption(f"... and {len(csv_not_found) - 20} more")
                    else:
                        st.info(f"✅ All {found_count} model ID(s) found in database")
            else:
                st.warning("⚠️ No model IDs found in CSV file")
                
        except Exception as e:
            st.error(f"❌ Error reading CSV file: {str(e)}")
            csv_model_ids = []
            st.session_state.csv_not_found = []
    
    # Store CSV IDs in session state
    if 'csv_model_ids' not in st.session_state:
        st.session_state.csv_model_ids = []
    
    # Update session state when CSV is uploaded or cleared
    if uploaded_file is not None and csv_model_ids:
        st.session_state.csv_model_ids = csv_model_ids
    elif uploaded_file is None:
        # Clear session state if no file uploaded
        if st.session_state.csv_model_ids:
            st.session_state.csv_model_ids = []
            st.session_state.csv_not_found = []
    
    # Clear CSV button
    if st.session_state.csv_model_ids:
        if st.button("🗑️ Clear CSV Upload", use_container_width=True):
            st.session_state.csv_model_ids = []
            st.session_state.csv_not_found = []
            st.rerun()
    
    st.markdown("---")
    st.header("🔍 Search Filters")
    
    # Text search
    search_term = st.text_input(
        "Search Text",
        placeholder="Model ID, BPS Name, or keywords...",
        help="Searches across: Model ID, Vegetation Type, Geographic Range, Biophysical Site Description, Vegetation Description, and BPS Name fields in the database tables (bps_models and ref_con_long). Does NOT search document content."
    )
    
    st.markdown("---")
    
    # Vegetation Type filter
    selected_vegetation = st.selectbox(
        "🌳 Vegetation Type",
        vegetation_types,
        index=0,
        help="Filters by the 'vegetation_type' field in the bps_models table. Examples: Forest and Woodland, Shrubland, Herbaceous, etc."
    )
    
    # Map Zone filter
    st.markdown("**🗺️ Map Zones**")
    map_zone_input = st.text_input(
        "Enter zone numbers (comma-separated)",
        placeholder="e.g., 1, 2, 3 or 7",
        help="Searches the 'map_zones' field in the bps_models table. Enter zone numbers like '1, 2, 3' or just '7'. Matches models where any of these zones appear in the comma-separated map_zones field."
    )
    
    # BPS Name filter
    bps_name_search = st.text_input(
        "🏷️ BPS Name Contains",
        placeholder="e.g., Oak, Aspen, Forest",
        help="Searches the 'bps_name' field in the ref_con_long table. Examples: 'Oak Woodland', 'Aspen Forest', 'Mountain'. This is the full Biophysical Setting name."
    )
    
    st.markdown("---")
    
    # Fire Frequency Filters
    st.markdown("**🔥 Fire Frequency Filters**")
    
    # Define preset ranges
    fire_presets = [
        ("No Filter", None),
        ("Very Frequent (< 10 years)", (0, 10)),
        ("Frequent (10-50 years)", (10, 50)),
        ("Moderate (50-100 years)", (50, 100)),
        ("Infrequent (100-500 years)", (100, 500)),
        ("Very Infrequent (500-1000 years)", (500, 1000)),
        ("Rare (> 1000 years)", (1000, None)),  # None means use max
        ("Custom Range", "custom")
    ]
    
    # Store filter values
    fire_filters = {}
    
    # Create dropdowns for each severity category
    severity_order = ['All Fires', 'Low (Surface)', 'Moderate (Mixed)', 'Replacement']
    for severity in severity_order:
        if severity in fire_ranges:
            range_info = fire_ranges[severity]
            min_val = range_info['min']
            max_val = range_info['max']
            
            # Create preset options for this severity
            preset_options = [preset[0] for preset in fire_presets]
            selected_preset = st.selectbox(
                f"{severity} Return Interval",
                preset_options,
                index=0,  # Default to "No Filter"
                key=f"fire_preset_{severity}",
                help=f"Filter models by {severity} fire return interval. Range: {min_val}-{max_val} years. Searches the fire_frequency table."
            )
            
            # Find the selected preset
            selected_range = None
            for preset_name, preset_range in fire_presets:
                if preset_name == selected_preset:
                    selected_range = preset_range
                    break
            
            # Handle custom range or preset
            if selected_range == "custom":
                # Show custom number inputs
                col1, col2 = st.columns(2)
                with col1:
                    custom_min = st.number_input(
                        f"{severity} Min (years)",
                        min_value=min_val,
                        max_value=max_val,
                        value=min_val,
                        key=f"fire_min_{severity}"
                    )
                with col2:
                    custom_max = st.number_input(
                        f"{severity} Max (years)",
                        min_value=min_val,
                        max_value=max_val,
                        value=max_val,
                        key=f"fire_max_{severity}"
                    )
                if custom_min <= custom_max:
                    fire_filters[severity] = (custom_min, custom_max)
            elif selected_range is not None:
                # Use preset range, handling None for max
                preset_min, preset_max = selected_range
                if preset_max is None:
                    preset_max = max_val  # Use full range max
                if preset_min < min_val:
                    preset_min = min_val
                if preset_max > max_val:
                    preset_max = max_val
                fire_filters[severity] = (preset_min, preset_max)
            # If "No Filter" selected, don't add to fire_filters
    
    st.markdown("---")
    
    # Results limit
    limit = st.number_input(
        "Results Limit",
        min_value=10,
        max_value=500,
        value=50,
        step=10,
        help="Maximum number of model results to display. Results come from the bps_models table joined with ref_con_long table."
    )
    
    # Clear filters button
    st.markdown("---")
    if st.button("🔄 Clear All Filters", use_container_width=True):
        st.rerun()

# Build query based on filters
query_conditions = []
query_params = []

# CSV Upload filter (takes priority if CSV is uploaded)
if st.session_state.csv_model_ids:
    # Use IN clause for CSV model IDs
    placeholders = ','.join(['?'] * len(st.session_state.csv_model_ids))
    query_conditions.append(f"bm.bps_model_id IN ({placeholders})")
    query_params.extend(st.session_state.csv_model_ids)

# Text search (only if no CSV upload)
if not st.session_state.csv_model_ids:
    if search_term and search_term.strip():
        query_conditions.append("""
            (bm.bps_model_id LIKE ? OR
             bm.vegetation_type LIKE ? OR
             bm.geographic_range LIKE ? OR
             bm.biophysical_site_description LIKE ? OR
             bm.vegetation_description LIKE ? OR
             rcl.bps_name LIKE ?)
        """)
        search_pattern = f"%{search_term.strip()}%"
        query_params.extend([search_pattern] * 6)

# Vegetation Type filter (can combine with CSV)
if selected_vegetation and selected_vegetation != 'All':
    # Use LIKE to match vegetation type even if it has map zone data appended
    query_conditions.append("bm.vegetation_type LIKE ?")
    query_params.append(f"{selected_vegetation}%")

# Map Zone filter (can combine with CSV)
if map_zone_input and map_zone_input.strip():
    # Parse comma-separated zone numbers
    try:
        zone_numbers = [int(z.strip()) for z in map_zone_input.split(',') if z.strip().isdigit()]
        if zone_numbers:
            # Create condition to check if any of the zones appear in map_zones
            zone_conditions = []
            for zone in zone_numbers:
                zone_conditions.append("(bm.map_zones LIKE ? OR bm.map_zones LIKE ? OR bm.map_zones = ? OR bm.map_zones LIKE ?)")
                query_params.extend([
                    f"%, {zone},%",  # Zone in middle: ", 7,"
                    f"{zone},%",     # Zone at start: "7,"
                    str(zone),       # Exact match: "7"
                    f"%{zone}%"      # Zone anywhere (fallback)
                ])
            query_conditions.append(f"({' OR '.join(zone_conditions)})")
    except Exception as e:
        st.warning(f"⚠️ Error parsing map zones: {e}")
        pass

# BPS Name filter (can combine with CSV)
if bps_name_search and bps_name_search.strip():
    query_conditions.append("rcl.bps_name LIKE ?")
    query_params.append(f"%{bps_name_search.strip()}%")

# Fire Frequency filters (can combine with CSV)
fire_freq_conditions = []
if fire_filters:
    for severity, (min_val, max_val) in fire_filters.items():
        # Add condition for any selected range (presets or custom)
        range_info = fire_ranges.get(severity, {})
        if range_info:
            fire_freq_conditions.append(f"""
                EXISTS (
                    SELECT 1 FROM fire_frequency ff
                    WHERE ff.bps_model_id = bm.bps_model_id
                    AND ff.severity = ?
                    AND ff."return_interval(years)" >= ?
                    AND ff."return_interval(years)" <= ?
                )
            """)
            query_params.extend([severity, min_val, max_val])
    
    if fire_freq_conditions:
        query_conditions.append(f"({' AND '.join(fire_freq_conditions)})")

# Build final query
if query_conditions:
    where_clause = " AND ".join(query_conditions)
    query = f"""
    SELECT DISTINCT
        bm.bps_model_id,
        bm.vegetation_type,
        bm.map_zones,
        bm.document,
        bm.vegetation_description,
        bm.geographic_range,
        bm.biophysical_site_description,
        bm.scale_description,
        bm.issues_or_problems,
        bm.native_uncharacteristic_conditions,
        rcl.bps_name
    FROM bps_models bm
    LEFT JOIN ref_con_long rcl ON bm.bps_model_id = rcl.bps_model_id
    WHERE {where_clause}
    ORDER BY bm.bps_model_id
    LIMIT ?
    """
    query_params.append(limit)
    
    # Execute query - ensure params is a tuple
    try:
        df = run_query(query, params=tuple(query_params))
    except Exception as e:
        st.error(f"Query error: {str(e)}")
        st.code(query)
        st.write("Parameters:", query_params)
        df = pd.DataFrame()  # Empty dataframe on error

# Display Options - Above Results
if query_conditions:
    st.markdown("---")
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown("")  # Spacer
    
    with col_right:
        with st.container():
            st.markdown("**📊 Display Options**")
            st.caption("Choose what to show in results")
            
            show_model_id = st.checkbox("Model ID", value=True, key="disp_model_id")
            show_bps_name = st.checkbox("BPS Name", value=True, key="disp_bps_name")
            show_vegetation_desc = st.checkbox("Vegetation Description", value=False, key="disp_veg_desc")
            show_geographic_range = st.checkbox("Geographic Range", value=False, key="disp_geo_range")
            show_biophysical_site = st.checkbox("Biophysical Site Description", value=False, key="disp_biophysical_site")
            show_scale_desc = st.checkbox("Scale Description", value=False, key="disp_scale_desc")
            show_issues = st.checkbox("Issues or Problems", value=False, key="disp_issues")
            show_uncharacteristic = st.checkbox("Native Uncharacteristic Conditions", value=False, key="disp_uncharacteristic")
            show_species = st.checkbox("BpS Dominant and Indicator Species", value=False, key="disp_species")
            show_succession = st.checkbox("Succession Class Descriptions", value=False, key="disp_succession")
            show_document = st.checkbox("Document Download", value=True, key="disp_document")
            show_fire_charts = st.checkbox("Fire Regime Charts", value=False, key="disp_fire_charts")
    
    st.markdown("---")
    
    # Display results
    if len(df) > 0:
        st.success(f"✅ Found {len(df)} model(s)")
        
        # Show active filters
        active_filters = []
        if st.session_state.csv_model_ids:
            active_filters.append(f"CSV Upload: {len(st.session_state.csv_model_ids)} model ID(s)")
        if search_term and not st.session_state.csv_model_ids:
            active_filters.append(f"Text: '{search_term}'")
        if selected_vegetation != 'All':
            active_filters.append(f"Vegetation: {selected_vegetation}")
        if map_zone_input:
            active_filters.append(f"Map Zones: {map_zone_input}")
        if bps_name_search:
            active_filters.append(f"BPS Name: '{bps_name_search}'")
        
        if active_filters:
            st.info("**Active Filters:** " + " | ".join(active_filters))
        
        # Show CSV validation info if CSV was uploaded
        if st.session_state.csv_model_ids and st.session_state.csv_not_found:
            st.warning(f"⚠️ Note: {len(st.session_state.csv_not_found)} model ID(s) from CSV were not found in database and are not shown in results.")
        
        st.markdown("---")
        
        # Bulk download options
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📦 Bulk Downloads**")
        
        # Initialize session state for selected models
        if 'selected_models' not in st.session_state:
            st.session_state.selected_models = set()
        
        # Select all / Deselect all buttons
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            if st.button("✅ Select All", use_container_width=True):
                st.session_state.selected_models = set(df['bps_model_id'].tolist())
                st.rerun()
        with col_sel2:
            if st.button("❌ Deselect All", use_container_width=True):
                st.session_state.selected_models = set()
                st.rerun()
        
        # If CSV uploaded, offer to auto-select all CSV results
        if st.session_state.csv_model_ids:
            csv_found_in_results = [mid for mid in st.session_state.csv_model_ids if mid in df['bps_model_id'].values]
            if csv_found_in_results and len(csv_found_in_results) != len(st.session_state.selected_models):
                if st.button(f"✅ Select All CSV Models ({len(csv_found_in_results)} found)", use_container_width=True):
                    st.session_state.selected_models = set(csv_found_in_results)
                    st.rerun()
        
        # Note: Download buttons will be shown after checkboxes are processed
        # to ensure accurate count
        
        st.markdown("---")
        
        # Display results with checkboxes
        for idx, row in df.iterrows():
            # Create document link if document exists
            doc_path = DOCS_PATH / row['document'] if row['document'] else None
            doc_exists = doc_path.exists() if doc_path else False
            
            # Build display title with bps_name prominently
            title_parts = [f"**{row['bps_model_id']}**"]
            if pd.notna(row['bps_name']) and row['bps_name']:
                title_parts.append(f"- {row['bps_name']}")
            if pd.notna(row['vegetation_type']) and row['vegetation_type']:
                title_parts.append(f"({row['vegetation_type']})")
            
            title = " ".join(title_parts)
            
            # Checkbox for selection
            model_id = row['bps_model_id']
            is_selected = model_id in st.session_state.selected_models
            
            col_check, col_title = st.columns([0.1, 9.9])
            with col_check:
                selected = st.checkbox(
                    "Select",
                    value=is_selected,
                    key=f"select_{model_id}",
                    label_visibility="hidden"
                )
                if selected and model_id not in st.session_state.selected_models:
                    st.session_state.selected_models.add(model_id)
                elif not selected and model_id in st.session_state.selected_models:
                    st.session_state.selected_models.remove(model_id)
            
            with col_title:
                with st.expander(title):
                    # Display sections based on user preferences
                    sections = []
                    
                    # Model ID section
                    if show_model_id:
                        sections.append(("Model ID", f"`{row['bps_model_id']}`"))
                    
                    # BPS Name section
                    if show_bps_name and pd.notna(row['bps_name']) and row['bps_name']:
                        sections.append(("BPS Name", row['bps_name']))
                    
                    # Vegetation Description section
                    if show_vegetation_desc and pd.notna(row['vegetation_description']) and row['vegetation_description']:
                        veg_desc = str(row['vegetation_description'])
                        # Show full description - no truncation
                        sections.append(("Vegetation Description", veg_desc))
                    
                    # Geographic Range section
                    if show_geographic_range and pd.notna(row['geographic_range']) and row['geographic_range']:
                        geo_range = str(row['geographic_range'])
                        # Show full range - no truncation
                        sections.append(("Geographic Range", geo_range))
                    
                    # Document Download section
                    if show_document:
                        sections.append(("Document", (doc_exists, doc_path, row['document'])))
                    
                    # Display sections in columns
                    if sections:
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            for section_name, section_content in sections:
                                if section_name == "Document":
                                    continue  # Handle separately
                                st.markdown(f"**{section_name}:**")
                                if section_name in ["Vegetation Description", "Geographic Range"]:
                                    # Get species list and italicize matches
                                    species_list = get_species_list_for_model(row['bps_model_id'])
                                    section_content_italicized = italicize_scientific_names_from_table(section_content, species_list)
                                    st.markdown(section_content_italicized)
                                else:
                                    st.markdown(section_content)
                                st.markdown("---")
                        
                        with col2:
                            # Document download
                            if show_document:
                                st.markdown("**Document:**")
                                # Get document info
                                doc_name = row['document'] if pd.notna(row['document']) else None
                                if doc_exists and doc_path:
                                    with open(doc_path, 'rb') as f:
                                        doc_bytes = f.read()
                                    st.download_button(
                                        label="📄 Download Document",
                                        data=doc_bytes,
                                        file_name=doc_name,
                                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                        key=f"download_{row['bps_model_id']}_{idx}"
                                    )
                                    st.caption(f"File: {doc_name}")
                                elif doc_name:
                                    st.warning(f"Document not found: {doc_name}")
                                else:
                                    st.info("No document available")
                    
                    # Biophysical Site Description section (expandable for long content)
                    if show_biophysical_site and pd.notna(row.get('biophysical_site_description')) and row.get('biophysical_site_description'):
                        st.markdown("---")
                        with st.expander("🌍 Biophysical Site Description", expanded=False):
                            bio_desc = str(row['biophysical_site_description'])
                            # Get species list and italicize matches
                            species_list = get_species_list_for_model(row['bps_model_id'])
                            bio_desc_italicized = italicize_scientific_names_from_table(bio_desc, species_list)
                            st.markdown(bio_desc_italicized)
                    
                    # Scale Description section (expandable for long content)
                    if show_scale_desc and pd.notna(row.get('scale_description')) and row.get('scale_description'):
                        st.markdown("---")
                        with st.expander("📏 Scale Description", expanded=False):
                            scale_desc = str(row['scale_description'])
                            # Get species list and italicize matches
                            species_list = get_species_list_for_model(row['bps_model_id'])
                            scale_desc_italicized = italicize_scientific_names_from_table(scale_desc, species_list)
                            st.markdown(scale_desc_italicized)
                    
                    # Issues or Problems section (expandable for long content)
                    if show_issues and pd.notna(row.get('issues_or_problems')) and row.get('issues_or_problems'):
                        st.markdown("---")
                        with st.expander("⚠️ Issues or Problems", expanded=False):
                            issues = str(row['issues_or_problems'])
                            # Get species list and italicize matches
                            species_list = get_species_list_for_model(row['bps_model_id'])
                            issues_italicized = italicize_scientific_names_from_table(issues, species_list)
                            st.markdown(issues_italicized)
                    
                    # Native Uncharacteristic Conditions section (expandable for long content)
                    if show_uncharacteristic and pd.notna(row.get('native_uncharacteristic_conditions')) and row.get('native_uncharacteristic_conditions'):
                        st.markdown("---")
                        with st.expander("🚫 Native Uncharacteristic Conditions", expanded=False):
                            unchar = str(row['native_uncharacteristic_conditions'])
                            # Get species list and italicize matches
                            species_list = get_species_list_for_model(row['bps_model_id'])
                            unchar_italicized = italicize_scientific_names_from_table(unchar, species_list)
                            st.markdown(unchar_italicized)
                    
                    # BpS Dominant and Indicator Species section (table)
                    if show_species:
                        st.markdown("---")
                        st.markdown("**🌿 BpS Dominant and Indicator Species**")
                        species_query = """
                        SELECT 
                            symbol,
                            scientific_name,
                            common_name
                        FROM bps_indicators
                        WHERE bps_model_id = ?
                        ORDER BY scientific_name
                        """
                        species_df = run_query(species_query, params=(row['bps_model_id'],))
                        if len(species_df) > 0:
                            # Use native Streamlit dataframe for reliable display (no raw HTML)
                            st.dataframe(
                                species_df,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "symbol": st.column_config.TextColumn("Symbol", width="small"),
                                    "scientific_name": st.column_config.TextColumn("Scientific Name", width="medium"),
                                    "common_name": st.column_config.TextColumn("Common Name", width="medium"),
                                }
                            )
                        else:
                            st.info("No species indicator data available for this model.")
                    
                    # Succession Class Descriptions section (single expandable section with structured data)
                    if show_succession:
                        st.markdown("---")
                        st.markdown("**🔄 Succession Class Descriptions**")
                        succession_query = """
                        SELECT 
                            scl.ref_label,
                            scl.state_class_id,
                            scl.description,
                            rcl.ref_percent
                        FROM scls_descriptions scl
                        LEFT JOIN ref_con_long rcl ON scl.bps_model_id = rcl.bps_model_id AND scl.ref_label = rcl.ref_label
                        WHERE scl.bps_model_id = ?
                        ORDER BY scl.ref_label
                        """
                        succession_df = run_query(succession_query, params=(row['bps_model_id'],))
                        if len(succession_df) > 0:
                            # Display as expandable sections for each class
                            for _, scls_row in succession_df.iterrows():
                                ref_label = str(scls_row['ref_label']) if pd.notna(scls_row['ref_label']) else 'Unknown'
                                state_class_id = str(scls_row['state_class_id']) if pd.notna(scls_row['state_class_id']) else 'N/A'
                                description = str(scls_row['description']) if pd.notna(scls_row['description']) else 'No description available'
                                ref_percent = scls_row['ref_percent'] if pd.notna(scls_row['ref_percent']) else None
                                
                                # Format ref_percent if available
                                ref_percent_str = f" ({ref_percent:.1f}%)" if ref_percent is not None else ""
                                
                                with st.expander(f"**{ref_label}{ref_percent_str}** (State Class: {state_class_id})", expanded=False):
                                    # Get species list and italicize matches
                                    species_list = get_species_list_for_model(row['bps_model_id'])
                                    description_italicized = italicize_scientific_names_from_table(description, species_list)
                                    st.markdown(description_italicized)
                        else:
                            st.info("No succession class descriptions available for this model.")
                    
                    # Fire Regime Charts section
                    if show_fire_charts:
                        st.markdown("---")
                        st.markdown("**🔥 Fire Regime Charts**")
                        
                        # Get fire frequency data for this model
                        fire_query = """
                        SELECT 
                            severity,
                            "return_interval(years)" as return_interval,
                            percent_of_all_fires as percent
                        FROM fire_frequency
                        WHERE bps_model_id = ?
                        AND severity IS NOT NULL
                        ORDER BY percent DESC
                        """
                        fire_df = run_query(fire_query, params=(row['bps_model_id'],))
                        
                        if len(fire_df) > 0:
                            st.subheader("Return Intervals by Severity")
                            # Horizontal bar chart of return intervals using Altair
                            chart = alt.Chart(fire_df).mark_bar().encode(
                                x=alt.X('return_interval:Q', title='Return Interval (years)'),
                                y=alt.Y('severity:N', title='Severity', sort='-x'),
                                tooltip=['severity', 'return_interval', 'percent']
                            ).properties(
                                width=600,
                                height=300
                            )
                            st.altair_chart(chart, use_container_width=True)
                            
                            # Data table with wrapping
                            st.markdown("**Fire Frequency Data:**")
                            # Use st.dataframe with column configuration for better wrapping
                            st.dataframe(
                                fire_df,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "severity": st.column_config.TextColumn("Severity", width="medium"),
                                    "return_interval": st.column_config.NumberColumn("Return Interval (years)", format="%.1f", width="medium"),
                                    "percent": st.column_config.NumberColumn("Percent of All Fires", format="%.1f%%", width="medium")
                                }
                            )
                        else:
                            st.info("No fire frequency data available for this model.")
        
        # Download buttons for selected models - placed after checkbox processing
        # to ensure accurate count
        if st.session_state.selected_models:
            num_selected = len(st.session_state.selected_models)  # Recalculate after checkboxes
            st.markdown("---")
            with st.expander("ℹ️ What's included in bulk downloads?", expanded=False):
                st.markdown("""
                **📦 ZIP Download (Selected Documents):**
                - Contains all Word (.docx) documents for the selected models
                - Only includes documents that exist in the database
                - Files are named with their original document names
                - Use this to download multiple model documents at once
                
                **📄 PDF Report:**
                - Contains a formatted report with all selected models
                - Includes only the display options you've selected:
                  - Model ID (if enabled)
                  - BPS Name (if enabled)
                  - Vegetation Description (if enabled) - **Full text, not truncated**
                  - Geographic Range (if enabled) - **Full text, not truncated**
                  - Biophysical Site Description (if enabled) - **Full text, not truncated**
                  - Scale Description (if enabled) - **Full text, not truncated**
                  - Issues or Problems (if enabled) - **Full text, not truncated**
                  - Native Uncharacteristic Conditions (if enabled) - **Full text, not truncated**
                  - BpS Dominant and Indicator Species (if enabled) - **Table format**
                  - Succession Class Descriptions (if enabled) - **Full descriptions with percentages**
                  - Fire Regime Charts data (if enabled) - includes charts and tables with severity, return intervals, and percentages
                - Each model appears on its own page
                - Shows active filters used for the search
                - Perfect for sharing or printing reports
                """)
            
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                # Create ZIP of selected documents
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    added_count = 0
                    for model_id in st.session_state.selected_models:
                        model_row = df[df['bps_model_id'] == model_id]
                        if not model_row.empty:
                            doc_name = model_row.iloc[0]['document']
                            if pd.notna(doc_name):
                                doc_path = DOCS_PATH / doc_name
                                if doc_path.exists():
                                    zip_file.write(doc_path, doc_name)
                                    added_count += 1
                
                if added_count > 0:
                    zip_buffer.seek(0)
                    st.download_button(
                        label=f"📦 Download {num_selected} Selected Documents (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name=f"bps_documents_{num_selected}_models.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                else:
                    st.warning("No documents found for selected models")
            
            with col_dl2:
                # Create PDF report function - capture current display options
                # Store display options in local variables to ensure they're captured
                # Debug: Print to verify values (will show in logs)
                pdf_show_model_id = bool(show_model_id)
                pdf_show_bps_name = bool(show_bps_name)
                pdf_show_vegetation_desc = bool(show_vegetation_desc)
                pdf_show_geographic_range = bool(show_geographic_range)
                pdf_show_biophysical_site = bool(show_biophysical_site)
                pdf_show_scale_desc = bool(show_scale_desc)
                pdf_show_issues = bool(show_issues)
                pdf_show_uncharacteristic = bool(show_uncharacteristic)
                pdf_show_species = bool(show_species)
                pdf_show_succession = bool(show_succession)
                pdf_show_fire_charts = bool(show_fire_charts)
                
                def create_pdf_report():
                    # Use captured display option values
                    buffer = io.BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=letter)
                    story = []
                    styles = getSampleStyleSheet()
                    
                    # Title
                    title_style = ParagraphStyle(
                        'CustomTitle',
                        parent=styles['Heading1'],
                        fontSize=18,
                        textColor=colors.HexColor('#2E7D32'),
                        spaceAfter=30,
                        alignment=TA_CENTER
                    )
                    story.append(Paragraph("BPS Database Explorer - Report", title_style))
                    story.append(Spacer(1, 0.2*inch))
                    
                    # Active filters
                    if active_filters:
                        story.append(Paragraph("<b>Active Filters:</b> " + " | ".join(active_filters), styles['Normal']))
                        story.append(Spacer(1, 0.1*inch))
                    
                    story.append(Paragraph(f"<b>Total Models:</b> {num_selected}", styles['Normal']))
                    story.append(Spacer(1, 0.3*inch))
                    
                    # Display options summary
                    display_options_used = []
                    if pdf_show_model_id:
                        display_options_used.append("Model ID")
                    if pdf_show_bps_name:
                        display_options_used.append("BPS Name")
                    if pdf_show_vegetation_desc:
                        display_options_used.append("Vegetation Description")
                    if pdf_show_geographic_range:
                        display_options_used.append("Geographic Range")
                    if pdf_show_biophysical_site:
                        display_options_used.append("Biophysical Site Description")
                    if pdf_show_scale_desc:
                        display_options_used.append("Scale Description")
                    if pdf_show_issues:
                        display_options_used.append("Issues or Problems")
                    if pdf_show_uncharacteristic:
                        display_options_used.append("Native Uncharacteristic Conditions")
                    if pdf_show_species:
                        display_options_used.append("BpS Dominant and Indicator Species")
                    if pdf_show_succession:
                        display_options_used.append("Succession Class Descriptions")
                    if pdf_show_fire_charts:
                        display_options_used.append("Fire Regime Charts")
                    
                    if display_options_used:
                        story.append(Paragraph(f"<b>Display Options Used:</b> {', '.join(display_options_used)}", styles['Normal']))
                        story.append(Spacer(1, 0.2*inch))
                    
                    # Debug info (will help verify fire charts is being checked)
                    if pdf_show_fire_charts:
                        story.append(Paragraph(f"<i>Note: Fire Regime Charts option is ENABLED - fire data will be included for each model.</i>", styles['Italic']))
                        story.append(Spacer(1, 0.1*inch))
                    
                    # Process each selected model
                    for model_id in sorted(st.session_state.selected_models):
                        model_row = df[df['bps_model_id'] == model_id]
                        if model_row.empty:
                            continue
                        
                        row = model_row.iloc[0]
                        
                        # Model header
                        header_style = ParagraphStyle(
                            'ModelHeader',
                            parent=styles['Heading2'],
                            fontSize=14,
                            textColor=colors.HexColor('#1976D2'),
                            spaceAfter=12,
                            spaceBefore=12
                        )
                        model_title = f"{row['bps_model_id']}"
                        if pd.notna(row['bps_name']) and row['bps_name']:
                            model_title += f" - {row['bps_name']}"
                        story.append(Paragraph(model_title, header_style))
                        
                        # Model ID
                        if pdf_show_model_id:
                            story.append(Paragraph(f"<b>Model ID:</b> {row['bps_model_id']}", styles['Normal']))
                            story.append(Spacer(1, 0.1*inch))
                        
                        # BPS Name
                        if pdf_show_bps_name and pd.notna(row['bps_name']) and row['bps_name']:
                            story.append(Paragraph(f"<b>BPS Name:</b> {row['bps_name']}", styles['Normal']))
                            story.append(Spacer(1, 0.1*inch))
                        
                        # Vegetation Description
                        if pdf_show_vegetation_desc and pd.notna(row['vegetation_description']) and row['vegetation_description']:
                            veg_desc = str(row['vegetation_description'])
                            # Get species list and italicize matches for PDF
                            species_list = get_species_list_for_model(model_id)
                            veg_desc = italicize_scientific_names_from_table_html(veg_desc, species_list)
                            # Show full description in PDF - split into paragraphs if very long
                            story.append(Paragraph("<b>Vegetation Description:</b>", styles['Normal']))
                            # Split long text into multiple paragraphs for better PDF formatting
                            if len(veg_desc) > 3000:
                                # Split by sentences for better readability
                                sentences = veg_desc.split('. ')
                                current_para = ""
                                for sentence in sentences:
                                    if len(current_para) + len(sentence) < 2000:
                                        current_para += sentence + ". "
                                    else:
                                        if current_para:
                                            story.append(Paragraph(current_para.strip(), styles['Normal']))
                                        current_para = sentence + ". "
                                if current_para:
                                    story.append(Paragraph(current_para.strip(), styles['Normal']))
                            else:
                                story.append(Paragraph(veg_desc, styles['Normal']))
                            story.append(Spacer(1, 0.1*inch))
                        
                        # Geographic Range
                        if pdf_show_geographic_range and pd.notna(row['geographic_range']) and row['geographic_range']:
                            geo_range = str(row['geographic_range'])
                            # Get species list and italicize matches for PDF
                            species_list = get_species_list_for_model(model_id)
                            geo_range = italicize_scientific_names_from_table_html(geo_range, species_list)
                            # Show full range in PDF - split into paragraphs if very long
                            story.append(Paragraph("<b>Geographic Range:</b>", styles['Normal']))
                            if len(geo_range) > 3000:
                                # Split by sentences for better readability
                                sentences = geo_range.split('. ')
                                current_para = ""
                                for sentence in sentences:
                                    if len(current_para) + len(sentence) < 2000:
                                        current_para += sentence + ". "
                                    else:
                                        if current_para:
                                            story.append(Paragraph(current_para.strip(), styles['Normal']))
                                        current_para = sentence + ". "
                                if current_para:
                                    story.append(Paragraph(current_para.strip(), styles['Normal']))
                            else:
                                story.append(Paragraph(geo_range, styles['Normal']))
                            story.append(Spacer(1, 0.1*inch))
                        
                        # Biophysical Site Description
                        if pdf_show_biophysical_site and pd.notna(row.get('biophysical_site_description')) and row.get('biophysical_site_description'):
                            bio_desc = str(row['biophysical_site_description'])
                            # Get species list and italicize matches for PDF
                            species_list = get_species_list_for_model(model_id)
                            bio_desc = italicize_scientific_names_from_table_html(bio_desc, species_list)
                            story.append(Paragraph("<b>Biophysical Site Description:</b>", styles['Normal']))
                            if len(bio_desc) > 3000:
                                sentences = bio_desc.split('. ')
                                current_para = ""
                                for sentence in sentences:
                                    if len(current_para) + len(sentence) < 2000:
                                        current_para += sentence + ". "
                                    else:
                                        if current_para:
                                            story.append(Paragraph(current_para.strip(), styles['Normal']))
                                        current_para = sentence + ". "
                                if current_para:
                                    story.append(Paragraph(current_para.strip(), styles['Normal']))
                            else:
                                story.append(Paragraph(bio_desc, styles['Normal']))
                            story.append(Spacer(1, 0.1*inch))
                        
                        # Scale Description
                        if pdf_show_scale_desc and pd.notna(row.get('scale_description')) and row.get('scale_description'):
                            scale_desc = str(row['scale_description'])
                            # Get species list and italicize matches for PDF
                            species_list = get_species_list_for_model(model_id)
                            scale_desc = italicize_scientific_names_from_table_html(scale_desc, species_list)
                            story.append(Paragraph("<b>Scale Description:</b>", styles['Normal']))
                            if len(scale_desc) > 3000:
                                sentences = scale_desc.split('. ')
                                current_para = ""
                                for sentence in sentences:
                                    if len(current_para) + len(sentence) < 2000:
                                        current_para += sentence + ". "
                                    else:
                                        if current_para:
                                            story.append(Paragraph(current_para.strip(), styles['Normal']))
                                        current_para = sentence + ". "
                                if current_para:
                                    story.append(Paragraph(current_para.strip(), styles['Normal']))
                            else:
                                story.append(Paragraph(scale_desc, styles['Normal']))
                            story.append(Spacer(1, 0.1*inch))
                        
                        # Issues or Problems
                        if pdf_show_issues and pd.notna(row.get('issues_or_problems')) and row.get('issues_or_problems'):
                            issues = str(row['issues_or_problems'])
                            # Get species list and italicize matches for PDF
                            species_list = get_species_list_for_model(model_id)
                            issues = italicize_scientific_names_from_table_html(issues, species_list)
                            story.append(Paragraph("<b>Issues or Problems:</b>", styles['Normal']))
                            if len(issues) > 3000:
                                sentences = issues.split('. ')
                                current_para = ""
                                for sentence in sentences:
                                    if len(current_para) + len(sentence) < 2000:
                                        current_para += sentence + ". "
                                    else:
                                        if current_para:
                                            story.append(Paragraph(current_para.strip(), styles['Normal']))
                                        current_para = sentence + ". "
                                if current_para:
                                    story.append(Paragraph(current_para.strip(), styles['Normal']))
                            else:
                                story.append(Paragraph(issues, styles['Normal']))
                            story.append(Spacer(1, 0.1*inch))
                        
                        # Native Uncharacteristic Conditions
                        if pdf_show_uncharacteristic and pd.notna(row.get('native_uncharacteristic_conditions')) and row.get('native_uncharacteristic_conditions'):
                            unchar = str(row['native_uncharacteristic_conditions'])
                            # Get species list and italicize matches for PDF
                            species_list = get_species_list_for_model(model_id)
                            unchar = italicize_scientific_names_from_table_html(unchar, species_list)
                            story.append(Paragraph("<b>Native Uncharacteristic Conditions:</b>", styles['Normal']))
                            if len(unchar) > 3000:
                                sentences = unchar.split('. ')
                                current_para = ""
                                for sentence in sentences:
                                    if len(current_para) + len(sentence) < 2000:
                                        current_para += sentence + ". "
                                    else:
                                        if current_para:
                                            story.append(Paragraph(current_para.strip(), styles['Normal']))
                                        current_para = sentence + ". "
                                if current_para:
                                    story.append(Paragraph(current_para.strip(), styles['Normal']))
                            else:
                                story.append(Paragraph(unchar, styles['Normal']))
                            story.append(Spacer(1, 0.1*inch))
                        
                        # BpS Dominant and Indicator Species (table)
                        if pdf_show_species:
                            story.append(Paragraph("<b>BpS Dominant and Indicator Species:</b>", styles['Normal']))
                            story.append(Spacer(1, 0.05*inch))
                            
                            species_query = """
                            SELECT 
                                symbol,
                                scientific_name,
                                common_name
                            FROM bps_indicators
                            WHERE bps_model_id = ?
                            ORDER BY scientific_name
                            """
                            
                            try:
                                pdf_conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
                                species_df_report = pd.read_sql_query(species_query, pdf_conn, params=(model_id,))
                                pdf_conn.close()
                                
                                if len(species_df_report) > 0:
                                    species_table_data = [['Symbol', 'Scientific Name', 'Common Name']]
                                    for _, species_row in species_df_report.iterrows():
                                        symbol = str(species_row['symbol']) if pd.notna(species_row['symbol']) else 'N/A'
                                        sci_name = str(species_row['scientific_name']) if pd.notna(species_row['scientific_name']) else 'N/A'
                                        # No italicization - just plain text
                                        common_name = str(species_row['common_name']) if pd.notna(species_row['common_name']) else 'N/A'
                                        species_table_data.append([symbol, sci_name, common_name])
                                    
                                    species_table = Table(species_table_data, colWidths=[1.5*inch, 2.5*inch, 2*inch])
                                    species_table.setStyle(TableStyle([
                                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                                    ]))
                                    story.append(species_table)
                                else:
                                    story.append(Paragraph("<i>No species indicator data available for this model.</i>", styles['Italic']))
                                story.append(Spacer(1, 0.1*inch))
                            except Exception as e:
                                story.append(Paragraph(f"<i>Error retrieving species data: {str(e)}</i>", styles['Italic']))
                                story.append(Spacer(1, 0.1*inch))
                        
                        # Succession Class Descriptions (no table, just full descriptions)
                        if pdf_show_succession:
                            story.append(Paragraph("<b>Succession Class Descriptions:</b>", styles['Normal']))
                            story.append(Spacer(1, 0.05*inch))
                            
                            succession_query = """
                            SELECT 
                                scl.ref_label,
                                scl.state_class_id,
                                scl.description,
                                rcl.ref_percent
                            FROM scls_descriptions scl
                            LEFT JOIN ref_con_long rcl ON scl.bps_model_id = rcl.bps_model_id AND scl.ref_label = rcl.ref_label
                            WHERE scl.bps_model_id = ?
                            ORDER BY scl.ref_label
                            """
                            
                            try:
                                pdf_conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
                                succession_df_report = pd.read_sql_query(succession_query, pdf_conn, params=(model_id,))
                                pdf_conn.close()
                                
                                if len(succession_df_report) > 0:
                                    # Add full descriptions (no table)
                                    for _, scls_row in succession_df_report.iterrows():
                                        ref_label = str(scls_row['ref_label']) if pd.notna(scls_row['ref_label']) else 'Unknown'
                                        state_class_id = str(scls_row['state_class_id']) if pd.notna(scls_row['state_class_id']) else 'N/A'
                                        description = str(scls_row['description']) if pd.notna(scls_row['description']) else 'No description available'
                                        ref_percent = scls_row['ref_percent'] if pd.notna(scls_row['ref_percent']) else None
                                        
                                        # Format ref_percent if available
                                        ref_percent_str = f" ({ref_percent:.1f}%)" if ref_percent is not None else ""
                                        
                                        # Get species list and italicize matches for PDF
                                        species_list = get_species_list_for_model(model_id)
                                        description = italicize_scientific_names_from_table_html(description, species_list)
                                        
                                        story.append(Paragraph(f"<b>{ref_label}{ref_percent_str}</b> (State Class: {state_class_id})", styles['Normal']))
                                        if len(description) > 2000:
                                            sentences = description.split('. ')
                                            current_para = ""
                                            for sentence in sentences:
                                                if len(current_para) + len(sentence) < 1500:
                                                    current_para += sentence + ". "
                                                else:
                                                    if current_para:
                                                        story.append(Paragraph(current_para.strip(), styles['Normal']))
                                                    current_para = sentence + ". "
                                            if current_para:
                                                story.append(Paragraph(current_para.strip(), styles['Normal']))
                                        else:
                                            story.append(Paragraph(description, styles['Normal']))
                                        story.append(Spacer(1, 0.1*inch))
                                else:
                                    story.append(Paragraph("<i>No succession class descriptions available for this model.</i>", styles['Italic']))
                                story.append(Spacer(1, 0.1*inch))
                            except Exception as e:
                                story.append(Paragraph(f"<i>Error retrieving succession class data: {str(e)}</i>", styles['Italic']))
                                story.append(Spacer(1, 0.1*inch))
                        
                        # Fire Regime Charts data
                        if pdf_show_fire_charts:
                            story.append(Paragraph("<b>Fire Regime Data:</b>", styles['Normal']))
                            story.append(Spacer(1, 0.05*inch))
                            
                            fire_query = """
                            SELECT 
                                severity,
                                "return_interval(years)" as return_interval,
                                percent_of_all_fires as percent
                            FROM fire_frequency
                            WHERE bps_model_id = ?
                            AND severity IS NOT NULL
                            ORDER BY percent DESC
                            """
                            
                            fire_df_report = None
                            error_msg = None
                            
                            try:
                                # Use direct connection for PDF generation (avoid caching issues)
                                pdf_conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
                                fire_df_report = pd.read_sql_query(fire_query, pdf_conn, params=(model_id,))
                                pdf_conn.close()
                                
                                # Debug: Always show what we got
                                if fire_df_report is None:
                                    error_msg = "Query returned None"
                                elif len(fire_df_report) == 0:
                                    error_msg = f"No fire data found for model {model_id}"
                                    
                            except Exception as e:
                                error_msg = f"Database error: {str(e)}"
                                fire_df_report = None
                            
                            # Always show something when fire charts option is enabled
                            if error_msg:
                                story.append(Paragraph(f"<i>{error_msg}</i>", styles['Italic']))
                                story.append(Spacer(1, 0.1*inch))
                            elif fire_df_report is not None and len(fire_df_report) > 0:
                                # Create table - ensure we have data
                                try:
                                    table_data = [['Severity', 'Return Interval (years)', 'Percent of All Fires']]
                                    for _, fire_row in fire_df_report.iterrows():
                                        severity = str(fire_row['severity']) if pd.notna(fire_row['severity']) else 'N/A'
                                        return_int_val = fire_row['return_interval']
                                        return_int = f"{return_int_val:.1f}" if pd.notna(return_int_val) else 'N/A'
                                        percent_val = fire_row['percent']
                                        percent = f"{percent_val:.1f}%" if pd.notna(percent_val) else 'N/A'
                                        table_data.append([severity, return_int, percent])
                                    
                                    # Only create table if we have data rows
                                    if len(table_data) > 1:  # More than just header
                                        # Create horizontal bar chart
                                        try:
                                            fig, ax = plt.subplots(figsize=(6, 3))
                                            severities = fire_df_report['severity'].tolist()
                                            return_intervals = fire_df_report['return_interval'].tolist()
                                            
                                            # Create horizontal bar chart
                                            y_pos = range(len(severities))
                                            ax.barh(y_pos, return_intervals, color='steelblue')
                                            ax.set_yticks(y_pos)
                                            ax.set_yticklabels(severities)
                                            ax.set_xlabel('Return Interval (years)')
                                            ax.set_title('Fire Return Intervals by Severity')
                                            ax.invert_yaxis()  # Top to bottom
                                            
                                            plt.tight_layout()
                                            
                                            # Save to buffer
                                            chart_buffer = io.BytesIO()
                                            plt.savefig(chart_buffer, format='png', dpi=100, bbox_inches='tight')
                                            chart_buffer.seek(0)
                                            plt.close()
                                            
                                            # Add chart image to PDF
                                            chart_img = Image(chart_buffer, width=5*inch, height=2.5*inch)
                                            story.append(chart_img)
                                            story.append(Spacer(1, 0.1*inch))
                                        except Exception as chart_error:
                                            story.append(Paragraph(f"<i>Could not generate chart: {str(chart_error)}</i>", styles['Italic']))
                                        
                                        # Add data table
                                        fire_table = Table(table_data, colWidths=[2*inch, 2*inch, 2*inch])
                                        fire_table.setStyle(TableStyle([
                                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                            ('FONTSIZE', (0, 0), (-1, 0), 10),
                                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                                        ]))
                                        story.append(fire_table)
                                        story.append(Spacer(1, 0.2*inch))
                                    else:
                                        story.append(Paragraph(f"<i>Fire data query returned empty results for model {model_id}.</i>", styles['Italic']))
                                        story.append(Spacer(1, 0.1*inch))
                                except Exception as table_error:
                                    story.append(Paragraph(f"<i>Error creating fire data table: {str(table_error)}</i>", styles['Italic']))
                                    story.append(Spacer(1, 0.1*inch))
                            else:
                                story.append(Paragraph(f"<i>No fire frequency data found for model {model_id}. Query returned: {fire_df_report}</i>", styles['Italic']))
                                story.append(Spacer(1, 0.1*inch))
                        
                        story.append(PageBreak())
                    
                    doc.build(story)
                    buffer.seek(0)
                    return buffer.getvalue()
                
                pdf_data = create_pdf_report()
                st.download_button(
                    label=f"📄 Download PDF Report ({num_selected} models)",
                    data=pdf_data,
                    file_name=f"bps_report_{num_selected}_models.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    else:
        st.warning("❌ No models found matching your filter criteria.")
        st.info("💡 Try adjusting your filters or clearing them to see more results.")
else:
    # Set default display options when no filters applied
    show_model_id = True
    show_bps_name = True
    show_vegetation_desc = False
    show_geographic_range = False
    show_biophysical_site = False
    show_scale_desc = False
    show_issues = False
    show_uncharacteristic = False
    show_species = False
    show_succession = False
    show_document = True
    show_fire_charts = False
    # No filters applied - show info
    if st.session_state.csv_model_ids:
        st.info(f"📤 CSV uploaded with {len(st.session_state.csv_model_ids)} model ID(s), but no matching models found. Check your model IDs or try adjusting filters.")
    else:
        st.info("👆 Use the filters in the sidebar or upload a CSV file to search for models")
    st.markdown("---")
    
    # Show some statistics
    col1, col2, col3 = st.columns(3)
    
    total_models = run_query("SELECT COUNT(DISTINCT bps_model_id) as count FROM bps_models").iloc[0]['count']
    total_vegetation_types = len(vegetation_types) - 1  # Subtract 'All'
    total_map_zones = len(map_zones_list)
    
    with col1:
        st.metric("Total Models", total_models)
    with col2:
        st.metric("Vegetation Types", total_vegetation_types)
    with col3:
        st.metric("Map Zones", total_map_zones)
    
    st.markdown("---")
    st.markdown("### 💡 How to Use Filters:")
    st.markdown("""
    - **Search Text**: Search across Model ID, BPS Name, and descriptions
    - **Vegetation Type**: Select from dropdown (or "All" for no filter)
    - **Map Zones**: Enter zone numbers like `1, 2, 3` or just `7`
    - **BPS Name**: Filter by keywords in BPS names (e.g., "Oak", "Aspen")
    - **Combine Filters**: Use multiple filters together for precise searches
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**BPS Database Explorer**")
st.sidebar.caption("Enhanced Model Search")
