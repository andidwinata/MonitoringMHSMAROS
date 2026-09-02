import streamlit as st
import pandas as pd
import io

st.set_page_config(
    page_title="Monitoring Penjualan & Insentif (SS / RSM / GRSM)",
    page_icon="🏢",
    layout="wide"
)

# 1. Target SKU per Channel (Berdasarkan 3 digit awal Channel)
DEFAULT_TARGET_CHANNEL = {
    '111': 7,   # Kios / Retail Small
    '154': 7,   # Wet Retail
    '113': 10,  # Retail Large
    '114': 15,  # Semi Grosir
    '115': 15,  # Grosir Kelontong
    '110': 25   # Grosir Modern / Supermarket
}

# 2. Master 61 SKU Must Have SKU (MHS)
DEFAULT_MHS_LIST = [
    '410583', '411008', '370150', '370152', '370153', '370193', '370095', '410832', '410834', '410835',
    '410871', '410820', '410821', '410822', '410823', '410824', '410825', '410826', '315486', '315580',
    '410695', '410696', '410697', '410291', '410332', '410905', '410846', '410881', '410901', '410864',
    '411014', '410737', '410868', '316857', '370118', '370141', '370143', '370144', '370146', '370176',
    '370177', '370178', '410584', '410882', '410991', '410992', '410803', '410804', '410805', '410806',
    '410807', '410808', '410809', '410810', '410884', '410885', '410886', '410887', '410888', '410889', '410890'
]

# --- FUNGSI PARSER LBP TXT (MENGATASI TRAILING PIPE) ---
def parse_raw_lbp(uploaded_file):
    if uploaded_file.name.endswith(('.txt', '.csv')):
        raw_bytes = uploaded_file.read()
        lines = raw_bytes.decode('utf-8', errors='ignore').splitlines()
        cleaned_lines = []
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            # Buang pipe kosong di ujung baris data
            if line_str.endswith('|'):
                line_str = line_str[:-1]
            cleaned_lines.append(line_str)
        
        first_line = cleaned_lines[0] if cleaned_lines else ""
        sep = '|' if '|' in first_line else ('\t' if '\t' in first_line else (';' if ';' in first_line else ','))
        df = pd.read_csv(io.StringIO('\n'.join(cleaned_lines)), sep=sep, low_memory=False)
    else:
        df = pd.read_excel(uploaded_file)
    
    df.columns = [str(c).strip() for c in df.columns]
    return df

# --- SIDEBAR PARAMETER ---
st.sidebar.title("⚙️ Pengaturan Operasional")
st.sidebar.markdown("**Akses:** SS / RSM / GRSM")

cb_standpro = st.sidebar.number_input(
    "Target Standpro (CB Area):",
    min_value=1,
    value=1090,
    step=25,
    help="Target Base Customer (CB) Standpro area untuk menentukan tier insentif dan % coverage."
)

target_sales_rp = st.sidebar.number_input(
    "Target Omset Penjualan (Rp, Opsional):",
    min_value=0,
    value=0,
    step=10000000,
    help="Isi jika ingin memantau % Achievement Omset terhadap Target."
)

uploaded_lbp = st.sidebar.file_uploader("📂 Upload File LBP (.txt / .csv / .xlsx)", type=['txt', 'csv', 'xlsx'])
uploaded_mhs = st.sidebar.file_uploader("📋 Upload Master MHS Baru (Opsional)", type=['csv', 'xlsx'])

# --- PEMROSESAN DATA & DASHBOARD ---
if uploaded_lbp is not None:
    try:
        with st.spinner("Memproses data LBP..."):
            df_raw = parse_raw_lbp(uploaded_lbp)

            # Master MHS
            if uploaded_mhs is not None:
                df_ref = pd.read_excel(uploaded_mhs) if uploaded_mhs.name.endswith('.xlsx') else pd.read_csv(uploaded_mhs)
                mhs_pcode_set = set(df_ref['Pcode'].astype(str).str.strip().unique())
            else:
                mhs_pcode_set = set(DEFAULT_MHS_LIST)

            # Standardisasi Tipe Data
            df_raw['Salesman'] = df_raw['Salesman'].astype(str).str.strip()
            df_raw['Pcode_Str'] = df_raw['Pcode'].astype(str).str.strip()
            df_raw['QTYPCS'] = pd.to_numeric(df_raw['QTYPCS'], errors='coerce').fillna(0)
            df_raw['AMOUNT'] = pd.to_numeric(df_raw['AMOUNT'], errors='coerce').fillna(0)
            df_raw['Kabupaten'] = df_raw['Kabupaten'].fillna('LAINNYA').astype(str).str.strip()
            df_raw['Kecamatan'] = df_raw['Kecamatan'].fillna('LAINNYA').astype(str).str.strip()
            
            # Hitung Faktur vs Retur
            is_retur = df_raw['TRANSTYPE'].astype(str).str.strip().str.upper() == 'R'
            df_raw['NET_QTY'] = df_raw['QTYPCS'].where(~is_retur, -df_raw['QTYPCS'])
            df_raw['NET_AMOUNT'] = df_raw['AMOUNT'].where(~is_retur, -df_raw['AMOUNT'])
            df_raw['RETUR_AMOUNT'] = df_raw['AMOUNT'].where(is_retur, 0)
            df_raw['BRUTO_AMOUNT'] = df_raw['AMOUNT'].where(~is_retur, 0)

            all_salesmen = sorted(df_raw['Salesman'].dropna().unique().tolist())

        # --- FILTER TIM SALESMAN (MULTI-SELECT UNTUK SPV) ---
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👥 **Pilih Salesman (Tim SPV)**")
            select_all = st.checkbox("Pilih Semua Salesman (Total Area)", value=True)
            
            if select_all:
                selected_salesmen = st.multiselect("Salesman Terpilih:", options=all_salesmen, default=all_salesmen)
            else:
                selected_salesmen = st.multiselect("Salesman Terpilih:", options=all_salesmen, default=all_salesmen[:3] if len(all_salesmen) >= 3 else all_salesmen)

        if not selected_salesmen:
            st.warning("Silakan pilih minimal 1 salesman pada menu di sebelah kiri.")
            st.stop()

        # Filter data sesuai salesman yang dipilih SPV
        df = df_raw[df_raw['Salesman'].isin(selected_salesmen)].copy()

        # Perhitungan Realisasi MHS per Outlet (Distinct SKU)
        df_mhs_tx = df[df['Pcode_Str'].isin(mhs_pcode_set)].copy()
        agg_sku = df_mhs_tx.groupby(['No Outlet', 'Pcode_Str'])['NET_QTY'].sum().reset_index()
        valid_mhs = agg_sku[agg_sku['NET_QTY'] > 0]
        sku_per_toko = valid_mhs.groupby('No Outlet').size().reset_index(name='Realisasi SKU Sold')

        # Profil Master Toko Terfilter
        outlet_master = df[['No Outlet', 'Nama Outlet', 'Kode Sales', 'Salesman', 'Channel', 'Kabupaten', 'Kecamatan']].drop_duplicates(subset=['No Outlet'])
        calc_toko = pd.merge(outlet_master, sku_per_toko, on='No Outlet', how='left').fillna({'Realisasi SKU Sold': 0})
        calc_toko['Realisasi SKU Sold'] = calc_toko['Realisasi SKU Sold'].astype(int)

        calc_toko['Channel_Prefix'] = calc_toko['Channel'].astype(str).str.slice(0, 3)
        calc_toko['Target SKU'] = calc_toko['Channel_Prefix'].map(DEFAULT_TARGET_CHANNEL).fillna(7).astype(int)
        calc_toko['Status Lolos'] = (calc_toko['Realisasi SKU Sold'] >= calc_toko['Target SKU']).astype(int)
        calc_toko['Gap SKU'] = (calc_toko['Target SKU'] - calc_toko['Realisasi SKU Sold']).apply(lambda x: max(0, x))

        # KPI Makro Area Terfilter
        total_ec = len(calc_toko)
        total_lolos_mhs = calc_toko['Status Lolos'].sum()
        ach_cb_standpro = (total_lolos_mhs / cb_standpro) * 100
        
        total_net_sales = df['NET_AMOUNT'].sum()
        total_bruto = df['BRUTO_AMOUNT'].sum()
        total_retur = df['RETUR_AMOUNT'].sum()
        retur_rate = (total_retur / total_bruto * 100) if total_bruto > 0 else 0

        # Tier Insentif
        if ach_cb_standpro >= 80: tier_label = "Tier 4 (≥ 80%) [MAX]"
        elif ach_cb_standpro >= 70: tier_label = "Tier 3 (70% - 79.9%)"
        elif ach_cb_standpro >= 60: tier_label = "Tier 2 (60% - 69.9%)"
        elif ach_cb_standpro >= 50: tier_label = "Tier 1 (50% - 59.9%)"
        else: tier_label = "< 50% (Belum Lolos Tier)"

        gap_toko_t1 = max(0, int(cb_standpro * 0.5) - total_lolos_mhs)

        # --- TAMPILAN DASHBOARD ---
        st.title("📊 Monitoring Operasional & Eksekutif Sales (SS / RSM / GRSM)")
        st.caption(f"Menampilkan data untuk **{len(selected_salesmen)} Salesman Terpilih** | Target Standpro: **{cb_standpro:,} Toko**")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📌 Ringkasan Eksekutif", 
            "👥 Kinerja Tim Salesman", 
            "📍 Omset & Sebaran Wilayah",
            "📦 Subbrand & Divisi", 
            "🎯 Action Plan Toko (Gap MHS)"
        ])

        # TAB 1: RINGKASAN EKSEKUTIF
        with tab1:
            st.subheader("Ringkasan Metrik Utama")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Omset Bersih (Net)", f"Rp {total_net_sales:,.0f}")
            c2.metric("Toko Transaksi (EC)", f"{total_ec:,} Toko")
            c3.metric("Toko Lolos MHS", f"{total_lolos_mhs:,} Toko")
            c4.metric("% Pencapaian vs Standpro", f"{ach_cb_standpro:.2f}%")

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Omset Bruto", f"Rp {total_bruto:,.0f}")
            c6.metric("Retur Rate", f"{retur_rate:.2f}%", delta=f"-Rp {total_retur:,.0f}", delta_color="inverse")
            c7.metric("Status Insentif Tim", tier_label)
            c8.metric("Kekurangan ke Tier 1 (50%)", f"{gap_toko_t1:,} Toko" if gap_toko_t1 > 0 else "✅ Tercapai")

            if target_sales_rp > 0:
                ach_val = (total_net_sales / target_sales_rp) * 100
                st.progress(min(ach_val / 100, 1.0))
                st.caption(f"Pencapaian Omset vs Target (Rp {target_sales_rp:,.0f}): **{ach_val:.2f}%**")

        # TAB 2: KINERJA SALESMAN
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

            display_sales = sales_perf.copy()
            display_sales['Net_Sales (Rp)'] = display_sales['Net_Sales'].apply(lambda x: f"Rp {x:,.0f}")
            display_sales['Drop Size / Faktur'] = display_sales['Drop Size / Faktur'].apply(lambda x: f"Rp {x:,.0f}")
            display_sales['% Strike Rate MHS'] = display_sales['% Strike Rate MHS'].apply(lambda x: f"{x:.1f}%")

            st.dataframe(
                display_sales[['Kode Sales', 'Salesman', 'Net_Sales (Rp)', 'EC', 'Toko_Lolos_MHS', '% Strike Rate MHS', 'Avg_SKU', 'Drop Size / Faktur']],
                use_container_width=True
            )

        # TAB 3: OMSET & SEBARAN WILAYAH
        with tab3:
            st.subheader("Analisis Penjualan per Wilayah")
            col_kab, col_kec = st.columns(2)

            with col_kab:
                st.markdown("**Penjualan per Kabupaten:**")
                kab_val = df.groupby('Kabupaten')['NET_AMOUNT'].sum().reset_index()
                kab_out = calc_toko.groupby('Kabupaten').agg(
                    Total_Toko=('No Outlet', 'count'),
                    Toko_Lolos=('Status Lolos', 'sum')
                ).reset_index()
                kab_merge = pd.merge(kab_val, kab_out, on='Kabupaten').sort_values(by='NET_AMOUNT', ascending=False)
                kab_merge['Omset (Rp)'] = kab_merge['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                kab_merge['Kontribusi (%)'] = ((kab_merge['NET_AMOUNT'] / total_net_sales) * 100).round(1)
                kab_merge['Strike Rate (%)'] = ((kab_merge['Toko_Lolos'] / kab_merge['Total_Toko']) * 100).round(1)
                
                st.dataframe(
                    kab_merge[['Kabupaten', 'Omset (Rp)', 'Kontribusi (%)', 'Total_Toko', 'Toko_Lolos', 'Strike Rate (%)']],
                    use_container_width=True
                )

            with col_kec:
                st.markdown("**Top 10 Kecamatan berdasarkan Omset:**")
                kec_val = df.groupby('Kecamatan')['NET_AMOUNT'].sum().reset_index()
                kec_out = calc_toko.groupby('Kecamatan').agg(
                    Total_Toko=('No Outlet', 'count'),
                    Toko_Lolos=('Status Lolos', 'sum')
                ).reset_index()
                kec_merge = pd.merge(kec_val, kec_out, on='Kecamatan').sort_values(by='NET_AMOUNT', ascending=False).head(10)
                kec_merge['Omset (Rp)'] = kec_merge['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                kec_merge['Kontribusi (%)'] = ((kec_merge['NET_AMOUNT'] / total_net_sales) * 100).round(1)
                kec_merge['Strike Rate (%)'] = ((kec_merge['Toko_Lolos'] / kec_merge['Total_Toko']) * 100).round(1)

                st.dataframe(
                    kec_merge[['Kecamatan', 'Omset (Rp)', 'Kontribusi (%)', 'Total_Toko', 'Toko_Lolos', 'Strike Rate (%)']],
                    use_container_width=True
                )

        # TAB 4: SUBBRAND & DIVISI CONTRIBUTION
        with tab4:
            st.subheader("Kontribusi Subbrand & Divisi Produk")
            col_sb1, col_sb2 = st.columns(2)
            
            with col_sb1:
                st.markdown("**Top 10 Subbrand berdasarkan Omset:**")
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

            st.markdown("---")
            st.markdown("**Performa Channel (Tipe Toko):**")
            channel_rep = calc_toko.groupby('Channel').agg(
                Total_EC=('No Outlet', 'count'),
                Toko_Lolos=('Status Lolos', 'sum')
            ).reset_index()
            channel_rep['% Lolos Channel'] = ((channel_rep['Toko_Lolos'] / channel_rep['Total_EC']) * 100).round(1)
            st.dataframe(channel_rep.sort_values(by='Total_EC', ascending=False), use_container_width=True)

        # TAB 5: ACTION PLAN GAP MHS
        with tab5:
            st.subheader("🎯 Action Plan: Toko Belum Lolos (Prioritas Push SKU)")
            sls_options = ['SEMUA TIM SPV'] + selected_salesmen
            pilih_sales = st.selectbox("Pilih Salesman:", sls_options)

            df_action = calc_toko if pilih_sales == 'SEMUA TIM SPV' else calc_toko[calc_toko['Salesman'] == pilih_sales]
            df_gap = df_action[df_action['Status Lolos'] == 0].sort_values(by=['Gap SKU', 'Realisasi SKU Sold'], ascending=[True, False])

            st.write(f"Ditemukan **{len(df_gap):,}** toko yang belum lolos:")
            cols_gap = ['No Outlet', 'Nama Outlet', 'Salesman', 'Channel', 'Kabupaten', 'Target SKU', 'Realisasi SKU Sold', 'Gap SKU']
            st.dataframe(df_gap[cols_gap], use_container_width=True)

            # Export All Data
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                display_sales.to_excel(writer, sheet_name='PERFORMA_SALESMAN', index=False)
                df_gap[cols_gap].to_excel(writer, sheet_name='GAP_OUTLET_ACTION', index=False)
                calc_toko.to_excel(writer, sheet_name='DATABASE_OUTLET', index=False)

            st.download_button(
                label="📥 Download Laporan Lengkap (.xlsx)",
                data=buf.getvalue(),
                file_name="Laporan_Monitoring_Penjualan_MHS.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as err:
        st.error(f"Gagal memproses file LBP: {str(err)}")
else:
    st.info("👈 Silakan upload file **LBP.txt** pada menu sebelah kiri untuk mengenerate dashboard monitoring secara otomatis.")
