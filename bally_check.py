import streamlit as st
import pandas as pd

# Set page configuration
st.set_page_config(layout="wide", page_title="Farfetch Product Validator")

# --- HEADER ---
st.title("📦 Farfetch Product Validator")
st.markdown("Checking products by SKU (with zero-padding fix), Netta ID, and Optional ID.")

# --- SIDEBAR UPLOADS ---
st.sidebar.header("Upload Files")
assortment_file = st.sidebar.file_uploader("1. Upload Assortment (CSV)", type=['csv'])
geo_files = st.sidebar.file_uploader("2. Upload 6 GEO Exports (CSV)", type=['csv'], accept_multiple_files=True)

expected_geos = ["HK", "US", "DE", "CH", "JP", "AU"]

if assortment_file and geo_files:
    # --- 1. PROCESS ASSORTMENT ---
    df_assort = pd.read_csv(assortment_file)
    
    # Identify Assortment Columns: A=SKU, B=Netta ID, C=Optional ID
    main_sku_col = df_assort.columns[0]
    netta_id_col = df_assort.columns[1]
    opt_id_col = df_assort.columns[2]
    
    # Create a clean version of the assortment for matching
    df_results = pd.DataFrame()
    # Strip .0, whitespace, and leading zeros from the assortment SKUs
    df_results['SKU'] = df_assort[main_sku_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.lstrip('0').str.upper()
    df_results['NETTA_ID'] = df_assort[netta_id_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
    df_results['OPT_ID'] = df_assort[opt_id_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()

    # --- 2. PROCESS EACH GEO FILE ---
    for uploaded_file in geo_files:
        geo_tag = "Unknown"
        for tag in expected_geos:
            if tag in uploaded_file.name.upper():
                geo_tag = tag
                break
        
        try:
            try:
                df_geo = pd.read_csv(uploaded_file)
            except:
                df_geo = pd.read_csv(uploaded_file, encoding='latin1')
            
            # Export Columns: A(0)=FF ID, F(5)=Partner Product ID, H(7)=Barcode/SKU
            ff_id_col = df_geo.columns[0]
            ff_partner_id_col = df_geo.columns[5]
            ff_sku_col = df_geo.columns[7]

            # Standardize Export Data
            df_geo_clean = df_geo[[ff_id_col, ff_sku_col, ff_partner_id_col]].copy()
            df_geo_clean.columns = ['FF_ID', 'FF_SKU', 'FF_PARTNER_ID']
            
            # CLEANING: Strip leading zeros from the export barcodes so they match the assortment
            df_geo_clean['FF_SKU'] = df_geo_clean['FF_SKU'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.lstrip('0').str.upper()
            df_geo_clean['FF_PARTNER_ID'] = df_geo_clean['FF_PARTNER_ID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
            df_geo_clean['FF_ID'] = df_geo_clean['FF_ID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()

            # Create Lookups (keep first occurrence)
            sku_lookup = df_geo_clean.drop_duplicates('FF_SKU').set_index('FF_SKU')['FF_ID'].to_dict()
            partner_id_lookup = df_geo_clean.drop_duplicates('FF_PARTNER_ID').set_index('FF_PARTNER_ID')['FF_ID'].to_dict()

            # --- MULTI-STEP LOGIC WITH SOURCE TRACKING ---
            def find_product_id(row):
                # Priority 1: SKU
                if row['SKU'] in sku_lookup:
                    return f"{sku_lookup[row['SKU']]}"
                # Priority 2: Netta ID
                if row['NETTA_ID'] in partner_id_lookup:
                    return f"{partner_id_lookup[row['NETTA_ID']]}"
                # Priority 3: Optional ID
                if row['OPT_ID'] in partner_id_lookup:
                    return f"{partner_id_lookup[row['OPT_ID']]}"
                return "Not Found"

            def find_source(row):
                if row['SKU'] in sku_lookup: return "SKU"
                if row['NETTA_ID'] in partner_id_lookup: return "Netta ID"
                if row['OPT_ID'] in partner_id_lookup: return "Opt ID"
                return "-"

            # Map the ID and the Method
            df_results[f"{geo_tag} ID"] = df_results.apply(find_product_id, axis=1)
            df_results[f"{geo_tag} Source"] = df_results.apply(find_source, axis=1)
            
        except Exception as e:
            st.warning(f"Could not process {uploaded_file.name}: {e}")

    # --- 3. FINAL DISPLAY ---
    # Hide the background matching columns
    final_display = df_results.drop(columns=['NETTA_ID', 'OPT_ID'])

    # Re-order columns so Source is next to the ID for each GEO
    cols = list(final_display.columns)
    id_cols = [c for c in cols if "ID" in c and c != "SKU"]
    sorted_cols = ["SKU"]
    for id_col in sorted_cols: # This is just a placeholder to build the list
        pass 
    
    # Custom sort to keep ID and Source pairs together
    final_cols = ["SKU"]
    for geo in expected_geos:
        if f"{geo} ID" in final_display.columns:
            final_cols.append(f"{geo} ID")
            final_cols.append(f"{geo} Source")

    final_display = final_display[final_cols]

    st.subheader("Coverage Summary")
    summary_cols = st.columns(len(expected_geos))
    for i, geo in enumerate(expected_geos):
        id_col = f"{geo} ID"
        if id_col in final_display.columns:
            found = (final_display[id_col] != "Not Found").sum()
            total = len(final_display)
            summary_cols[i].metric(label=geo, value=f"{found}/{total}")

    st.divider()
    st.subheader("Detailed Results")
    st.dataframe(
        final_display, 
        use_container_width=True,
        column_config={col: st.column_config.TextColumn(col) for col in final_display.columns}
    )

    # --- DOWNLOAD ---
    csv = final_display.to_csv(index=False).encode('utf-8')
    st.download_button("Download Results", csv, "farfetch_validation.csv", "text/csv")

else:
    st.info("Upload files to start.")
