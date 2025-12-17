import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("Farfetch Product Validator")

# 1. File Uploaders
st.sidebar.header("Upload Files")
assortment_file = st.sidebar.file_uploader("Upload Assortment (CSV)", type=['csv'])

# Multiple file uploader for the 6 GEO files
geo_files = st.sidebar.file_uploader("Upload 6 GEO Exports (CSV)", type=['csv'], accept_multiple_files=True)

# List of the GEOs we expect
expected_geos = ["HK", "US", "DE", "CH", "JP", "AU"]

if assortment_file and geo_files:
    # Load the assortment
    df_assortment = pd.read_csv(assortment_file)
    
    # Standardize column names (A, B, C based on your description)
    # We use .iloc to pick by position: 0=A, 1=B, 2=C
    sku_col = df_assortment.columns[0] 
    df_results = df_assortment[[sku_col]].copy()
    df_results.rename(columns={sku_col: "SKU"}, inplace=True)

    # Process each uploaded GEO file
    for uploaded_file in geo_files:
        # Check which GEO this file belongs to based on the filename
        # (Assuming the filename contains the GEO code like 'HK' or 'US')
        geo_name = "Unknown"
        for geo in expected_geos:
            if geo in uploaded_file.name.upper():
                geo_name = geo
                break
        
        # Load GEO export
        df_geo = pd.read_csv(uploaded_file)
        
        # Mapping based on your description:
        # Col H (index 7) = Partner barcode (SKU)
        # Col A (index 0) = Product ID (Farfetch ID)
        geo_sku_col = df_geo.columns[7]
        geo_id_col = df_geo.columns[0]
        
        # Create a dictionary for quick lookup: {Partner Barcode: Product ID}
        lookup_dict = pd.Series(df_geo[geo_id_col].values, index=df_geo[geo_sku_col]).to_dict()
        
        # Map the Farfetch ID to our main results table
        df_results[f"{geo_name} ID"] = df_results["SKU"].map(lookup_dict).fillna("Not Found")

    # Display the Result Table
    st.subheader("Validation Results")
    st.write("Below is the mapping of your Assortment SKUs to Farfetch Product IDs across GEOs:")
    st.dataframe(df_results, use_container_width=True)

    # Download link
    csv = df_results.to_csv(index=False).encode('utf-8')
    st.download_button("Download Results as CSV", csv, "validation_results.csv", "text/csv")

else:
    st.info("Please upload the Assortment file and all 6 GEO export files in the sidebar to begin.")
