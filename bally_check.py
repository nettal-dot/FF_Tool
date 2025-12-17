import streamlit as st
import pandas as pd

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
        # Identify GEO from filename
        geo_tag = "Unknown"
        for tag in expected_geos:
            if tag in uploaded_file.name.upper():
                geo_tag = tag
                break
        
        # Load the GEO export
        try:
            # Fallback encoding for different GEO exports
            try:
                df_geo = pd.read_csv(uploaded_file)
            except:
                df_geo = pd.read_csv(uploaded_file, encoding='latin1')
            
            # Extract Columns: A (0) is ID, H (7) is SKU
            ff_id_col = df_geo.columns[0]
            ff_sku_col = df_geo.columns[7]
            
            # Clean GEO data exactly like the assortment
            df_geo_clean = df_geo[[ff_id_col, ff_sku_col]].copy()
            df_geo_clean.columns = ['FF_ID', 'FF_SKU']
            df_geo_clean['FF_SKU'] = df_geo_clean['FF_SKU'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
            
            # Remove duplicates within the GEO file
            df_geo_clean = df_geo_clean.drop_duplicates(subset=['FF_SKU'])
            
            # Merge (Left Join)
            df_results = pd.merge(df_results, df_geo_clean, left_on='SKU', right_on='FF_SKU', how='left')
            
            # Rename the ID column and drop the extra SKU column from merge
            df_results.rename(columns={'FF_ID': f'{geo_tag} ID'}, inplace=True)
            df_results.drop(columns=['FF_SKU'], inplace=True)
            
        except Exception as e:
            st.warning(f"Could not process {uploaded_file.name}: {e}")

    # 3. Final Cleanup
    df_results = df_results.fillna("Not Found")

    # --- SUMMARY DASHBOARD ---
    st.subheader("Coverage Summary")
    cols = st.columns(len(expected_geos))
    for i, geo in enumerate(expected_geos):
        column_name = f"{geo} ID"
        if column_name in df_results.columns:
            count = (df_results[column_name] != "Not Found").sum()
            total = len(df_results)
            percentage = (count / total) * 100 if total > 0 else 0
            cols[i].metric(label=f"{geo} Found", value=f"{count}/{total}", delta=f"{percentage:.1f}%")

    # --- DATA TABLE ---
    st.divider()
    st.subheader("Detailed Results")
    st.dataframe(df_results, use_container_width=True)

    # --- DOWNLOAD ---
    csv = df_results.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Full Results as CSV",
        data=csv,
        file_name="farfetch_validation_results.csv",
        mime="text/csv",
    )

else:
    st.info("👋 Welcome! Please upload your Assortment file and the 6 Farfetch GEO exports in the sidebar to begin.")
