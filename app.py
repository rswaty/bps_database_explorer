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

@st.cache_resource
def get_connection():
    """Create and cache database connection"""
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

# Main title
st.title("🌲 BPS Database Explorer - Model Search")
st.markdown("---")

# Search interface
col1, col2 = st.columns([2, 1])

with col1:
    search_term = st.text_input(
        "Search by Model ID, BPS Name, Vegetation Type, or Description", 
        placeholder="e.g., 10080, Oak Woodland, Forest, Oak"
    )

with col2:
    limit = st.number_input("Results Limit", min_value=10, max_value=500, value=50, step=10)

if search_term:
    # Query to get models with bps_name
    query = """
    SELECT DISTINCT
        bm.bps_model_id,
        bm.vegetation_type,
        bm.map_zones,
        bm.document,
        rcl.bps_name
    FROM bps_models bm
    LEFT JOIN ref_con_long rcl ON bm.bps_model_id = rcl.bps_model_id
    WHERE 
        bm.bps_model_id LIKE ? OR
        bm.vegetation_type LIKE ? OR
        bm.geographic_range LIKE ? OR
        bm.biophysical_site_description LIKE ? OR
        bm.vegetation_description LIKE ? OR
        rcl.bps_name LIKE ?
    ORDER BY bm.bps_model_id
    LIMIT ?
    """
    search_pattern = f"%{search_term}%"
    df = run_query(query, params=(search_pattern, search_pattern, search_pattern, 
                                 search_pattern, search_pattern, search_pattern, limit))
    
    if len(df) > 0:
        st.success(f"Found {len(df)} models")
        
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
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                        st.caption(f"File: {row['document']}")
                    elif row['document']:
                        st.warning(f"Document not found: {row['document']}")
                    else:
                        st.info("No document available")
    else:
        st.warning("No models found matching your search criteria.")
else:
    st.info("👆 Enter a search term above to find models")
    st.markdown("---")
    st.markdown("### 💡 Search Tips:")
    st.markdown("""
    - Search by **Model ID** (e.g., `10080`, `10080_1_2_3_7`)
    - Search by **BPS Name** (e.g., `Oak Woodland`, `Aspen Forest`)
    - Search by **Vegetation Type** (e.g., `Forest`, `Woodland`)
    - Search by **keywords** in descriptions (e.g., `oak`, `fire`, `mountain`)
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**BPS Database Explorer**")
st.sidebar.caption("Model Search Interface")
