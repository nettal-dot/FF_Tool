import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("Farfetch Validator - Debug Mode")

st.sidebar.header("Upload Files")
assortment_file = st.sidebar.file_uploader("1. Assortment", type=['csv'])
geo_files = st.sidebar.file_uploader("2. GEO Exports", type=['csv'], accept_multiple_files=True)

if assortment_file and geo_files:
    # Load Assortment
    df_assort = pd.read_csv(assortment_file)
    sku_col_name = df_assort.columns[0]
    # Standardize Assortment SKU to String
    df_assort['SKU_CLEAN'] = df_assort[sku_col_name].astype(str).str.strip().str.upper()
    
    # Create the base results table
    df_results = df_assort[['SKU_CLEAN']].copy()
    df_results.rename(columns={'SKU_CLEAN': 'SKU'}, inplace=True)

    st.write("### Connection Status")

    for uploaded_file in geo_files:
        # Identify GEO
        geo_tag = "Unknown"
        for tag in ["HK", "US", "DE", "CH", "JP", "AU"]:
            if tag in uploaded_file.name.upper():
                geo_tag = tag
                break
        
        # Load the file
        df_geo = pd.read_csv(uploaded_file)
        
        # Farfetch columns: A=ID (0), H=Partner Barcode (7)
        ff_id_col = df_geo.columns[0]
        ff_sku_col = df_geo.columns[7]
        
        # CLEANING: Force both to strings and remove any decimals (.0)
        df_geo_clean = df_geo[[ff_id_col, ff_sku_col]].copy()
        df_geo_clean.columns = ['FF_ID', 'FF_SKU']
        
        df_geo_clean['FF_SKU'] = df_geo_clean['FF_SKU'].astype(str).str.strip().str.upper().str.replace(r'\.0$', '', regex=True)
        
        # Check for matches before merging
        matches = df_results['SKU'].isin(df_geo_clean['FF_SKU']).sum()
        
        if matches > 0:
            st.success(f"✅ **{geo_tag}**: Found {matches} matching SKUs.")
        else:
            st.error(f"❌ **{geo_tag}**: 0 matches found. (Checked {len(df_geo_clean)} rows in file)")
            # Show a sample to help us debug
            with st.expander(f"See data sample for {geo_tag}"):
                st.write("Assortment SKU sample:", df_results['SKU'].head(3).tolist())
                st.write(f"{geo_tag} File SKU sample:", df_geo_clean['FF_SKU'].head(3).tolist())

        # Final Merge
        df_geo_clean = df_geo_clean.drop_duplicates(subset=['FF_SKU'])
        df_results = pd.merge(df_results, df_geo_clean, left_on='SKU', right_on='FF_SKU', how='left')
        df_results.rename(columns={'FF_ID': f'{geo_tag}_ID'}, inplace=True)
        df_results.drop(columns=['FF_SKU'], inplace=True)

    st.divider()
    st.subheader("Final Result")
    st.dataframe(df_results.fillna("Not Found"))
