import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Farfetch Product Validator")

st.title("📦 Farfetch Product Validator & Migration Tool")

# --- SIDEBAR ---
st.sidebar.header("Upload Files")
assortment_file = st.sidebar.file_uploader("1. Upload Assortment (CSV)", type=['csv'])
geo_files = st.sidebar.file_uploader("2. Upload GEO Exports (CSV)", type=['csv'], accept_multiple_files=True)

# Your 4 critical target GEOs
target_geos = ["US", "AU", "HK", "CH"]
all_geos = ["HK", "US", "DE", "CH", "JP", "AU"]

if assortment_file and geo_files:
    # --- 1. PROCESS ASSORTMENT ---
    df_assort = pd.read_csv(assortment_file)
    main_sku_col, netta_id_col, opt_id_col = df_assort.columns[0], df_assort.columns[1], df_assort.columns[2]
    
    df_results = pd.DataFrame()
    df_results['SKU'] = df_assort[main_sku_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.lstrip('0').str.upper()
    df_results['NETTA_ID'] = df_assort[netta_id_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
    df_results['OPT_ID'] = df_assort[opt_id_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()

    # --- 2. PROCESS GEO FILES ---
    for uploaded_file in geo_files:
        geo_tag = "Unknown"
        for tag in all_geos:
            if tag in uploaded_file.name.upper():
                geo_tag = tag
                break
        
        try:
            try: df_geo = pd.read_csv(uploaded_file)
            except: df_geo = pd.read_csv(uploaded_file, encoding='latin1')
            
            ff_id_col, ff_partner_id_col, ff_sku_col = df_geo.columns[0], df_geo.columns[5], df_geo.columns[7]

            df_geo_clean = df_geo[[ff_id_col, ff_sku_col, ff_partner_id_col]].copy()
            df_geo_clean.columns = ['FF_ID', 'FF_SKU', 'FF_PARTNER_ID']
            
            for col in ['FF_SKU', 'FF_PARTNER_ID', 'FF_ID']:
                df_geo_clean[col] = df_geo_clean[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.lstrip('0').str.upper()

            sku_lookup = df_geo_clean.drop_duplicates('FF_SKU').set_index('FF_SKU')['FF_ID'].to_dict()
            partner_id_lookup = df_geo_clean.drop_duplicates('FF_PARTNER_ID').set_index('FF_PARTNER_ID')['FF_ID'].to_dict()

            def find_product_id(row):
                if row['SKU'] in sku_lookup: return sku_lookup[row['SKU']]
                if row['NETTA_ID'] in partner_id_lookup: return partner_id_lookup[row['NETTA_ID']]
                if row['OPT_ID'] in partner_id_lookup: return partner_id_lookup[row['OPT_ID']]
                return "Not Found"

            df_results[f"{geo_tag} ID"] = df_results.apply(find_product_id, axis=1)
            
        except Exception as e:
            st.warning(f"Error in {uploaded_file.name}: {e}")

    # --- 3. LOGIC FOR FARFETCH SUPPORT ---
    def get_migration_info(row):
        present_in = [g for g in target_geos if f"{g} ID" in row and row[f"{g} ID"] != "Not Found"]
        missing_in = [g for g in target_geos if f"{g} ID" in row and row[f"{g} ID"] == "Not Found"]
        
        # Get the first available Product ID to use as a reference
        all_ids = [row[f"{g} ID"] for g in target_geos if f"{g} ID" in row and row[f"{g} ID"] != "Not Found"]
        ref_id = all_ids[0] if all_ids else "N/A"
        
        return pd.Series([ref_id, ", ".join(present_in), ", ".join(missing_in)])

    # Create the migration table
    df_migration = df_results.apply(get_migration_info, axis=1)
    df_migration.columns = ['Product ID', 'Current GEOs', 'Target GEOs for Migration']
    
    # Only show rows that are missing in at least one target GEO AND present in at least one other
    df_migration = df_migration[(df_migration['Current GEOs'] != "") & (df_migration['Target GEOs for Migration'] != "")]
    df_migration = df_migration.drop_duplicates(subset=['Product ID'])

    # --- TABS FOR ORGANIZATION ---
    tab1, tab2 = st.tabs(["Full Checker Table", "🚀 Farfetch Migration Request"])

    with tab1:
        st.subheader("Master Validation Table")
        st.dataframe(df_results.drop(columns=['NETTA_ID', 'OPT_ID']), use_container_width=True)

    with tab2:
        st.subheader("List for Farfetch Support")
        st.info("Copy the table below to send to Farfetch. It shows which Product IDs need to be migrated to which GEOs.")
        st.dataframe(df_migration, use_container_width=True)
        
        csv_mig = df_migration.to_csv(index=False).encode('utf-8')
        st.download_button("Download Migration List", csv_mig, "farfetch_migration_request.csv", "text/csv")

else:
    st.info("Upload files to begin.")
