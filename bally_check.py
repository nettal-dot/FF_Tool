import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Farfetch Validator")
st.title("Farfetch Product Validator")

# 1. File Uploaders
st.sidebar.header("Upload Files")
assortment_file = st.sidebar.file_uploader("1. Upload Assortment (CSV)", type=['csv'])
geo_files = st.sidebar.file_uploader("2. Upload GEO Exports (CSV)", type=['csv'], accept_multiple_files=True)

expected_geos = ["HK", "US", "DE", "CH", "JP", "AU"]

if assortment_file and geo_files:
    # Load and clean assortment
    df_assortment = pd.read_csv(assortment_file)
    sku_col = df_assortment.columns[0]
    
    # Keep only the SKU column and remove any empty rows
    df_results = df_assortment[[sku_col]].copy()
    df_results.rename(columns={sku_col: "SKU"}, inplace=True)
    df_results = df_results.dropna(subset=["SKU"])
    df_results["SKU"] = df_results["SKU"].astype(str).str.strip()

    # Process each GEO file
    for uploaded_file in geo_files:
        # Detect GEO from filename
        geo_name = "Unknown"
        for geo in expected_geos:
            if geo in uploaded_file.name.upper():
                geo_name = geo
                break
        
        # Load and clean GEO export
        df_geo = pd.read_csv(uploaded_file)
        
        # Column H (Index 7) = SKU, Column A (Index 0) = Farfetch ID
        geo_sku_col = df_geo.columns[7]
        geo_id_col = df_geo.columns[0]
        
        # Select only the columns we need and clean them
        df_geo_subset = df_geo[[geo_sku_col, geo_id_col]].copy()
        df_geo_subset.columns = ["SKU", f"{geo_name} ID"]
        
        # Clean data: Remove blanks and convert to string to ensure matching works
        df_geo_subset = df_geo_subset.dropna(subset=["SKU"])
        df_geo_subset["SKU"] = df_geo_subset["SKU"].astype(str).str.strip()
        
        # Remove duplicates just in case there are hidden blanks or repeats
        df_geo_subset = df_geo_subset.drop_duplicates(subset=["SKU"])

        # Use MERGE instead of MAP (Left join keeps all assortment SKUs)
        df_results = pd.merge(df_results, df_geo_subset, on="SKU", how="left")

    # Fill empty matches with "Not Found"
    df_results = df_results.fillna("Not Found")

    # Display Results
    st.subheader("Validation Results")
    st.dataframe(df_results, use_container_width=True)

    # Download
    csv = df_results.to_csv(index=False).encode('utf-8')
    st.download_button("Download Results as CSV", csv, "validation_results.csv", "text/csv")

else:
    st.info("Waiting for files to be uploaded...")
