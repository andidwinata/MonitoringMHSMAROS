import streamlit as st
import pandas as pd
import io

st.set_page_config(
    page_title="Executive Sales Monitoring (SS / RSM / GRSM)",
    page_icon="🏢",
    layout="wide"
)

# --- 1. MASTER PARAMETER ---
DEFAULT_TARGET_CHANNEL = {
    '111': 7,   # Kios / Retail Small
    '154': 7,   # Wet Retail
    '113': 10,  # Retail Large
    '114': 15,  # Semi Grosir
    '115': 15,  # Grosir Kelontong
    '110': 25   # Grosir Modern / Supermarket
}

DEFAULT_MHS_LIST = [
    '410583', '411008', '370150', '370152', '370153', '370193', '370095', '410832', '410834', '410835',
    '410871', '410820', '410821', '410822', '410823', '410824', '410825', '410826', '315486', '315580',
    '410695', '410696', '410697', '410291', '410332', '410905', '410846', '410881', '410901', '410864',
    '411014', '410737', '410868', '316857', '370118', '370141', '370143', '370144', '370146', '370176',
    '370177', '370178', '410584', '410882', '410991', '410992', '410803', '410804', '410805', '410806',
    '410807', '410808', '410809', '410810', '410884', '410885', '410886', '410887', '410888', '410889', '410890'
]

# --- 2. SIDEBAR CONFIGURATION ---
st.sidebar.title("⚙️ Parameter Operational")
st.sidebar.markdown("**Role Access:** SS / RSM / GRSM")

cb_standpro = st.sidebar.number_input(
    "Target CB Cover / Standpro Area:",
    min_value=1,
    value=1090,
    step=25,
    help="Target Base Customer (CB) Standpro area untuk menentukan tier insentif dan % coverage."
)

target_sales_rp = st.sidebar.number_input(
    "Target Net Sales (Rp, Opsional):",
    min_value=0,
    value=0,
    step=10000000,
    help="Isi jika ingin memantau % Achievement Omset Value terhadap Target."
)

uploaded_lbp = st.sidebar.file_uploader("📂 Upload File LBP (.txt / .csv / .xlsx)", type=['txt', 'csv', 'xlsx'])
uploaded_mhs = st.sidebar.file_uploader("📋 Upload Master MHS Custom (Opsional)", type=['csv', 'xlsx'])

# --- 3. CORE PROCESSING ENGINE ---
if uploaded_lbp is not None:
    try:
        with st.spinner("Memproses seluruh metriks KPI dari LBP..."):
            # Load LBP dengan deteksi delimiter otomatis
            if uploaded_lbp.name.endswith(('.txt', '.csv')):
                raw_bytes = uploaded_lbp.read()
                sample = raw_bytes[:4096].decode('utf-8', errors='ignore')
                sep = '\t' if '\t' in sample else (';' if ';' in sample else (',' if ',' in sample else '|'))
                uploaded_lbp.seek(0)
                df = pd.read_csv(io.StringIO(raw_bytes.decode('utf-8', errors='ignore')), sep=sep, low_memory=False)
            else:
                df = pd.read_excel(uploaded_lbp)

            df.columns = [str(c).strip() for c in df.columns]

            # Master MHS List
            if uploaded_mhs is not None:
                df_ref = pd.read_excel(uploaded_mhs) if uploaded_mhs.name.endswith('.xlsx') else pd.read_csv(uploaded_mhs)
                mhs_pcode_set = set(df_ref['Pcode'].astype(str).str.strip().unique())
            else:
                mhs_pcode_set = set(DEFAULT_MHS_LIST)

            # Standardisasi Tipe Data Transaksi
            df['Pcode_Str'] = df['Pcode'].astype(str).str.strip()
            df['QTYPCS'] = pd.to_numeric(df['QTYPCS'], errors='coerce').fillna(0)
            df['AMOUNT'] = pd.to_numeric(df['AMOUNT'], errors='coerce').fillna(0)
            
            # Hitung Faktur vs Retur
            is_retur = df['TRANSTYPE'].astype(str).str.strip().str.upper() == 'R'
            df['NET_QTY'] = df['QTYPCS'].where(~is_retur, -df['QTYPCS'])
            df['NET_AMOUNT'] = df['AMOUNT'].where(~is_retur, -df['AMOUNT'])
            df['RETUR_AMOUNT'] = df['AMOUNT'].where(is_retur, 0)
            df['BRUTO_AMOUNT'] = df['AMOUNT'].where(~is_retur, 0)

            # Hitung MHS Outlet Level
            df_mhs_tx = df[df['Pcode_Str'].isin(mhs_pcode_set)].copy()
            agg_sku = df_mhs_tx.groupby(['No Outlet', 'Pcode_Str'])['NET_QTY'].sum().reset_index()
            valid_mhs = agg_sku[agg_sku['NET_QTY'] > 0]
            sku_per_toko = valid_mhs.groupby('No Outlet').size().reset_index(name='Realisasi SKU Sold')

            # Master Toko Tercover (EC)
            outlet_master = df[['No Outlet', 'Nama Outlet', 'Kode Sales', 'Salesman', 'Channel', 'Kabupaten', 'Kecamatan']].drop_duplicates(subset=['No Outlet'])
            calc_toko = pd.merge(outlet_master, sku_per_toko, on='No Outlet', how='left').fillna({'Realisasi SKU Sold': 0})
            calc_toko['Realisasi SKU Sold'] = calc_toko['Realisasi SKU Sold'].astype(int)

            calc_toko['Channel_Prefix'] = calc_toko['Channel'].astype(str).str.slice(0, 3)
            calc_toko['Target SKU'] = calc_toko['Channel_Prefix'].map(DEFAULT_TARGET_CHANNEL).fillna(7).astype(int)
            calc_toko['Status Lolos'] = (calc_toko['Realisasi SKU Sold'] >= calc_toko['Target SKU']).astype(int)
            calc_toko['Gap SKU'] = (calc_toko['Target SKU'] - calc_toko['Realisasi SKU Sold']).apply(lambda x: max(0, x))

            # --- KPI MAKRO AREA ---
            total_ec = len(calc_toko)
            total_lolos_mhs = calc_toko['Status Lolos'].sum()
            ach_cb_standpro = (total_lolos_mhs / cb_standpro) * 100
            
            total_net_sales = df['NET_AMOUNT'].sum()
            total_bruto = df['BRUTO_AMOUNT'].sum()
            total_retur = df['RETUR_AMOUNT'].sum()
            retur_rate = (total_retur / total_bruto * 100) if total_bruto > 0 else 0

            # Skema Tier Insentif
            if ach_cb_standpro >= 80: tier_label = "Tier 4 (≥ 80%) [MAX]"
            elif ach_cb_standpro >= 70: tier_label = "Tier 3 (70% - 79.9%)"
            elif ach_cb_standpro >= 60: tier_label = "Tier 2 (60% - 69.9%)"
            elif ach_cb_standpro >= 50: tier_label = "Tier 1 (50% - 59.9%)"
            else: tier_label = "< 50% (Belum Lolos Tier)"

        # --- TAMPILAN DASHBOARD MULTI-TAB ---
        st.title("📊 Monitoring Operasional & Eksekutif Sales (SS / RSM / GRSM)")
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📌 Executive Overview", 
            "👥 Sales Force Performance", 
            "📦 Subbrand & Divisi", 
            "🏬 Channel & Territory", 
            "🎯 MHS Gap Action Plan"
        ])

        # TAB 1: EXECUTIVE OVERVIEW (RSM / GRSM VIEW)
        with tab1:
            st.subheader("High-Level KPIs")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Net Sales Value", f"Rp {total_net_sales:,.0f}")
            c2.metric("Total Toko Transaksi (EC)", f"{total_ec:,} Toko")
            c3.metric("Toko Lolos MHS", f"{total_lolos_mhs:,} Toko")
            c4.metric("% Pencapaian vs CB Standpro", f"{ach_cb_standpro:.1f}%")

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Gross Sales", f"Rp {total_bruto:,.0f}")
            c6.metric("Retur Rate", f"{retur_rate:.2f}%", delta=f"-Rp {total_retur:,.0f}", delta_color="inverse")
            c7.metric("Status Insentif Area", tier_label)
            gap_toko_t1 = max(0, int(cb_standpro * 0.5) - total_lolos_mhs)
            c8.metric("Gap Toko ke Tier 1 (50%)", f"{gap_toko_t1:,} Toko" if gap_toko_t1 > 0 else "✅ Tercapai")

            if target_sales_rp > 0:
                ach_val = (total_net_sales / target_sales_rp) * 100
                st.progress(min(ach_val / 100, 1.0))
                st.caption(f"Achievement Sales Value vs Target (Rp {target_sales_rp:,.0f}): **{ach_val:.2f}%**")

        # TAB 2: SALES FORCE PERFORMANCE (SS VIEW)
        with tab2:
            st.subheader("Performa Tim Salesman")
            sales_val = df.groupby(['Kode Sales', 'Salesman']).agg(
                Net_Sales=('NET_AMOUNT', 'sum'),
                Total_Faktur=('Faktur', 'nunique')
            ).reset_index()

            sales_mhs = calc_toko.groupby(['Kode Sales', 'Salesman']).agg(
                EC=('No Outlet', 'count'),
                Toko_Lolos_MHS=('Status Lolos', 'sum'),
                Avg_SKU=('Realisasi SKU Sold', 'mean')
            ).reset_index()

            sales_perf = pd.merge(sales_val, sales_mhs, on=['Kode Sales', 'Salesman'])
            sales_perf['% Strike Rate MHS'] = ((sales_perf['Toko_Lolos_MHS'] / sales_perf['EC']) * 100).round(1)
            sales_perf['Drop Size / Faktur'] = (sales_perf['Net_Sales'] / sales_perf['Total_Faktur']).round(0)
            sales_perf['Avg_SKU'] = sales_perf['Avg_SKU'].round(1)

            # Format tampilan
            display_sales = sales_perf.copy()
            display_sales['Net_Sales (Rp)'] = display_sales['Net_Sales'].apply(lambda x: f"Rp {x:,.0f}")
            display_sales['Drop Size / Faktur'] = display_sales['Drop Size / Faktur'].apply(lambda x: f"Rp {x:,.0f}")

            st.dataframe(
                display_sales[['Kode Sales', 'Salesman', 'Net_Sales (Rp)', 'EC', 'Toko_Lolos_MHS', '% Strike Rate MHS', 'Avg_SKU', 'Drop Size / Faktur']],
                use_container_width=True
            )

        # TAB 3: SUBBRAND & DIVISI CONTRIBUTION
        with tab3:
            st.subheader("Kontribusi Subbrand & Kategori Produk")
            col_sb1, col_sb2 = st.columns(2)
            
            with col_sb1:
                st.markdown("**Top 10 Subbrand berdasarkan Omset Net:**")
                if 'SUBBRANDNAME' in df.columns:
                    top_sb = df.groupby('SUBBRANDNAME')['NET_AMOUNT'].sum().reset_index().sort_values(by='NET_AMOUNT', ascending=False).head(10)
                    top_sb['Net Omset (Rp)'] = top_sb['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                    top_sb['Kontribusi (%)'] = ((top_sb['NET_AMOUNT'] / total_net_sales) * 100).round(2)
                    st.dataframe(top_sb[['SUBBRANDNAME', 'Net Omset (Rp)', 'Kontribusi (%)']], use_container_width=True)

            with col_sb2:
                st.markdown("**Penjualan per Divisi:**")
                if 'Divisi' in df.columns:
                    div_sales = df.groupby('Divisi')['NET_AMOUNT'].sum().reset_index().sort_values(by='NET_AMOUNT', ascending=False)
                    div_sales['Net Omset (Rp)'] = div_sales['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                    div_sales['Kontribusi (%)'] = ((div_sales['NET_AMOUNT'] / total_net_sales) * 100).round(2)
                    st.dataframe(div_sales[['Divisi', 'Net Omset (Rp)', 'Kontribusi (%)']], use_container_width=True)

        # TAB 4: CHANNEL & TERRITORY
        with tab4:
            st.subheader("Performa per Tipe Toko & Rayon")
            col_ch, col_reg = st.columns(2)
            
            with col_ch:
                st.markdown("**Performa Channel (Tipe Toko):**")
                channel_rep = calc_toko.groupby('Channel').agg(
                    Total_EC=('No Outlet', 'count'),
                    Toko_Lolos=('Status Lolos', 'sum')
                ).reset_index()
                channel_rep['% Lolos Channel'] = ((channel_rep['Toko_Lolos'] / channel_rep['Total_EC']) * 100).round(1)
                st.dataframe(channel_rep.sort_values(by='Total_EC', ascending=False), use_container_width=True)

            with col_reg:
                st.markdown("**Performa per Kabupaten:**")
                if 'Kabupaten' in calc_toko.columns:
                    kab_rep = calc_toko.groupby('Kabupaten').agg(
                        Total_EC=('No Outlet', 'count'),
                        Toko_Lolos=('Status Lolos', 'sum')
                    ).reset_index()
                    kab_rep['% Lolos'] = ((kab_rep['Toko_Lolos'] / kab_rep['Total_EC']) * 100).round(1)
                    st.dataframe(kab_rep.sort_values(by='Total_EC', ascending=False), use_container_width=True)

        # TAB 5: ACTION PLAN GAP MHS
        with tab5:
            st.subheader("🎯 Action Plan: Toko Belum Lolos (Prioritas Push SKU)")
            sls_options = ['ALL'] + sorted(calc_toko['Salesman'].dropna().unique().tolist())
            pilih_sales = st.selectbox("Pilih Salesman:", sls_options)

            df_action = calc_toko if pilih_sales == 'ALL' else calc_toko[calc_toko['Salesman'] == pilih_sales]
            df_gap = df_action[df_action['Status Lolos'] == 0].sort_values(by=['Gap SKU', 'Realisasi SKU Sold'], ascending=[True, False])

            st.write(f"Ditemukan **{len(df_gap):,}** toko yang belum lolos:")
            cols_gap = ['No Outlet', 'Nama Outlet', 'Salesman', 'Channel', 'Target SKU', 'Realisasi SKU Sold', 'Gap SKU']
            st.dataframe(df_gap[cols_gap], use_container_width=True)

            # Export All Data
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                display_sales.to_excel(writer, sheet_name='PERFORMA_SALESMAN', index=False)
                df_gap[cols_gap].to_excel(writer, sheet_name='GAP_OUTLET_ACTION', index=False)
                calc_toko.to_excel(writer, sheet_name='DATABASE_OUTLET', index=False)

            st.download_button(
                label="📥 Download Executive Report (.xlsx)",
                data=buf.getvalue(),
                file_name="Laporan_Monitoring_Executive_SS_RSM.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as err:
        st.error(f"Gagal memproses file LBP: {str(err)}")
        st.info("Pastikan file LBP TXT memuat kolom utama: No Outlet, Nama Outlet, Kode Sales, Salesman, Channel, Pcode, QTYPCS, AMOUNT, TRANSTYPE.")
else:
    st.info("👈 Silakan upload file **LBP.txt** pada menu sebelah kiri untuk mengenerate dashboard monitoring SS / RSM / GRSM secara otomatis.")