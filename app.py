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
    
    st.markdown("---")
    
    # Display Options
    st.markdown("**📊 Display Options**")
    st.caption("Choose what to show in results")
    
    show_model_id = st.checkbox("Model ID", value=True, key="disp_model_id")
    show_bps_name = st.checkbox("BPS Name", value=True, key="disp_bps_name")
    show_vegetation_desc = st.checkbox("Vegetation Description", value=False, key="disp_veg_desc")
    show_geographic_range = st.checkbox("Geographic Range", value=False, key="disp_geo_range")
    show_document = st.checkbox("Document Download", value=True, key="disp_document")
    show_fire_charts = st.checkbox("Fire Regime Charts", value=False, key="disp_fire_charts")
    
    # Clear filters button
    st.markdown("---")
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
                    # Truncate if very long
                    if len(veg_desc) > 1000:
                        veg_desc = veg_desc[:1000] + "..."
                    sections.append(("Vegetation Description", veg_desc))
                
                # Geographic Range section
                if show_geographic_range and pd.notna(row['geographic_range']) and row['geographic_range']:
                    geo_range = str(row['geographic_range'])
                    # Truncate if very long
                    if len(geo_range) > 1000:
                        geo_range = geo_range[:1000] + "..."
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
                                st.write(section_content)
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
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Return Intervals by Severity")
                            # Bar chart of return intervals
                            chart_data = fire_df.set_index('severity')['return_interval']
                            st.bar_chart(chart_data)
                        
                        with col2:
                            st.subheader("Percent of All Fires")
                            # Bar chart of percentages
                            chart_data2 = fire_df.set_index('severity')['percent']
                            st.bar_chart(chart_data2)
                        
                        # Data table
                        st.markdown("**Fire Frequency Data:**")
                        st.dataframe(fire_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("No fire frequency data available for this model.")
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
