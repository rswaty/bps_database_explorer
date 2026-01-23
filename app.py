import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import os

# Page configuration
st.set_page_config(
    page_title="BPS Database Explorer",
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
    """Create and cache database connection"""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found: {DB_PATH}")
    return sqlite3.connect(str(DB_PATH))

@st.cache_data
def run_query(query, params=None):
    """Execute a query and return results as DataFrame"""
    conn = get_connection()
    if params:
        df = pd.read_sql_query(query, conn, params=params)
    else:
        df = pd.read_sql_query(query, conn)
    return df

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

# Main title
st.title("🌲 BPS Database Explorer - Model Search")
st.markdown("---")

# Get filter options
vegetation_types = get_vegetation_types()
map_zones_list = get_unique_map_zones()
fire_ranges = get_fire_frequency_ranges()

# Create filter sidebar
with st.sidebar:
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
        help="Filter by BPS name keywords"
    )
    
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
    if st.button("🔄 Clear All Filters", use_container_width=True):
        st.rerun()

# Build query based on filters
query_conditions = []
query_params = []

# Text search
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

# Vegetation Type filter
if selected_vegetation and selected_vegetation != 'All':
    # Use LIKE to match vegetation type even if it has map zone data appended
    query_conditions.append("bm.vegetation_type LIKE ?")
    query_params.append(f"{selected_vegetation}%")

# Map Zone filter
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

# BPS Name filter
if bps_name_search and bps_name_search.strip():
    query_conditions.append("rcl.bps_name LIKE ?")
    query_params.append(f"%{bps_name_search.strip()}%")

# Fire Frequency filters
fire_freq_conditions = []
if fire_filters:
    for severity, (min_val, max_val) in fire_filters.items():
        # Only add condition if slider is not at full range
        range_info = fire_ranges.get(severity, {})
        if range_info and (min_val != range_info['min'] or max_val != range_info['max']):
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
    
    # Display results
    if len(df) > 0:
        st.success(f"✅ Found {len(df)} model(s)")
        
        # Show active filters
        active_filters = []
        if search_term:
            active_filters.append(f"Text: '{search_term}'")
        if selected_vegetation != 'All':
            active_filters.append(f"Vegetation: {selected_vegetation}")
        if map_zone_input:
            active_filters.append(f"Map Zones: {map_zone_input}")
        if bps_name_search:
            active_filters.append(f"BPS Name: '{bps_name_search}'")
        
        if active_filters:
            st.info("**Active Filters:** " + " | ".join(active_filters))
        
        st.markdown("---")
        
        # Display results
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
            
            with st.expander(title):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    if pd.notna(row['bps_name']) and row['bps_name']:
                        st.markdown(f"**BPS Name:** {row['bps_name']}")
                    
                    st.markdown(f"**Model ID:** `{row['bps_model_id']}`")
                    
                    if pd.notna(row['vegetation_type']) and row['vegetation_type']:
                        st.markdown(f"**Vegetation Type:** {row['vegetation_type']}")
                    
                    if pd.notna(row['map_zones']) and row['map_zones']:
                        st.markdown(f"**Map Zones:** {row['map_zones']}")
                
                with col2:
                    st.markdown("**Document:**")
                    if doc_exists and doc_path:
                        # Create a download link for the document
                        with open(doc_path, 'rb') as f:
                            doc_bytes = f.read()
                        st.download_button(
                            label="📄 Download Document",
                            data=doc_bytes,
                            file_name=row['document'],
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"download_{idx}"
                        )
                        st.caption(f"File: {row['document']}")
                    elif row['document']:
                        st.warning(f"Document not found: {row['document']}")
                    else:
                        st.info("No document available")
    else:
        st.warning("❌ No models found matching your filter criteria.")
        st.info("💡 Try adjusting your filters or clearing them to see more results.")
else:
    # No filters applied - show info
    st.info("👆 Use the filters in the sidebar to search for models")
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
