import streamlit as st
import pandas as pd

# Set page configuration
st.set_page_config(layout="wide", page_title="Farfetch Product Validator")

# --- HEADER ---
st.title("📦 Farfetch Product Validator")
st.markdown("Upload your assortment and GEO exports to cross-reference Farfetch IDs.")

# --- SIDEBAR UPLOADS ---
st.sidebar.header("Upload Files")
assortment_file = st.sidebar.file_uploader("1. Upload Assortment (CSV)", type=['csv'])
geo_files = st.sidebar.file_uploader("2. Upload 6 GEO Exports (CSV)", type=['csv'], accept_multiple_files=True)

expected_geos = ["HK", "US", "DE", "CH", "JP", "AU"]

if assortment_file and geo_files:
    # 1. Process Assortment
    df_assort = pd.read_csv(assortment_file)
    sku_col_name = df_assort.columns[0]
    
    # Standardize Assortment SKU: String, No Decimals, No Spaces, Uppercase
    df_assort['SKU_CLEAN'] = df_assort[sku_col_name].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
    
    # Initialize the results table
    df_results = df_assort[['SKU_CLEAN']].copy()
    df_results.rename(columns={'SKU_CLEAN': 'SKU'}, inplace=True)

    # 2. Process each GEO file
    for uploaded_file in geo_files:
        # Identify GEO from filename (e.g., "BALLY AU - BALLY AU WH - 01")
        geo_tag = "Unknown"
        for tag in expected_geos:
            if tag in uploaded_file.name.upper():
                geo_tag = tag
                break
        
        # Load the GEO export
        try:
            # Handle different encodings automatically
            try:
                df_geo = pd.read_csv(uploaded_file)
            except:
                df_geo = pd.read_csv(uploaded_file, encoding='latin1')
            
            # Column H (Index 7) is SKU, Column A (Index 0) is Farfetch Product ID
            ff_id_col = df_geo.columns[0]
            ff_sku_col = df_geo.columns[7]
            
            # Clean GEO data exactly like the assortment for perfect matching
            df_geo_clean = df_geo[[ff_id_col, ff_sku_col]].copy()
            df_geo_clean.columns = ['FF_ID', 'FF_SKU']
            df_geo_clean['FF_SKU'] = df_geo_clean['FF_SKU'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
            
            # Remove duplicates within the GEO file to prevent merge errors
            df_geo_clean = df_geo_clean.drop_duplicates(subset=['FF_SKU'])
            
            # Merge into master list
            df_results = pd.merge(df_results, df_geo_clean, left_on='SKU', right_on='FF_SKU', how='left')
            
            # Rename the ID column to the GEO name and drop the helper SKU column
            df_results.rename(columns={'FF_ID': f'{geo_tag} ID'}, inplace=True)
            df_results.drop(columns=['FF_SKU'], inplace=True)
            
        except Exception as e:
            st.warning(f"Could not process {uploaded_file.name}: {e}")

    # --- 3. FINAL CLEANUP (Fixing the .0 issue) ---
    for col in df_results.columns:
        if col != "SKU":
            # Convert to string, strip .0, and handle 'nan'
            df_results[col] = df_results[col].astype(str).str.replace(r'\.0$', '', regex=True)
            df_results[col] = df_results[col].replace('nan', 'Not Found')

    # --- SUMMARY DASHBOARD ---
    st.subheader("Coverage Summary")
    summary_cols = st.columns(len(expected_geos))
    for i, geo in enumerate(expected_geos):
        column_name = f"{geo} ID"
        if column_name in df_results.columns:
            found_count = (df_results[column_name] != "Not Found").sum()
            total_count = len(df_results)
            percentage = (found_count / total_count) * 100 if total_count > 0 else 0
            summary_cols[i].metric(label=f"{geo}", value=f"{found_count}/{total_count}", delta=f"{percentage:.1f}%")

    # --- DATA TABLE ---
    st.divider()
    st.subheader("Detailed Results")
    
    # Using column_config to ensure IDs are displayed as plain text (no commas or decimals)
    st.dataframe(
        df_results, 
        use_container_width=True,
        column_config={col: st.column_config.TextColumn(col) for col in df_results.columns}
    )

    # --- DOWNLOAD ---
    csv = df_results.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Full Results as CSV",
        data=csv,
        file_name="farfetch_validation_results.csv",
        mime="text/csv",
    )

else:
    st.info("👋 Welcome! Please upload your Assortment file and the 6 GEO exports in the sidebar to begin.")
