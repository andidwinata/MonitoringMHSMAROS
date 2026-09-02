import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

st.set_page_config(
    page_title="Monitoring Penjualan & Insentif MHS",
    page_icon="📊",
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

# --- SIDEBAR OPERASIONAL ---
st.sidebar.title("⚙️ Pengaturan Operasional")
st.sidebar.markdown("**Akses:** SS / RSM / GRSM")

cb_standpro = st.sidebar.number_input(
    "Target Standpro (CB Area):",
    min_value=1,
    value=1090,
    step=25,
    help="Target Base Customer (CB) Standpro area untuk menghitung % pencapaian dan tier insentif."
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

            # Proteksi Kolom Wilayah & Pasar
            if 'Kabupaten' not in df_raw.columns:
                df_raw['Kabupaten'] = '-'
            else:
                df_raw['Kabupaten'] = df_raw['Kabupaten'].fillna('-').astype(str).str.strip()

            if 'Kecamatan' not in df_raw.columns:
                df_raw['Kecamatan'] = '-'
            else:
                df_raw['Kecamatan'] = df_raw['Kecamatan'].fillna('-').astype(str).str.strip()

            if 'Kode Pasar' not in df_raw.columns:
                df_raw['Kode Pasar'] = '-'
            else:
                df_raw['Kode Pasar'] = df_raw['Kode Pasar'].fillna('-').astype(str).str.strip()
            
            # Hitung Faktur vs Retur
            is_retur = df_raw['TRANSTYPE'].astype(str).str.strip().str.upper() == 'R'
            df_raw['NET_QTY'] = df_raw['QTYPCS'].where(~is_retur, -df_raw['QTYPCS'])
            df_raw['NET_AMOUNT'] = df_raw['AMOUNT'].where(~is_retur, -df_raw['AMOUNT'])
            df_raw['RETUR_AMOUNT'] = df_raw['AMOUNT'].where(is_retur, 0)
            df_raw['BRUTO_AMOUNT'] = df_raw['AMOUNT'].where(~is_retur, 0)

            all_salesmen = sorted(df_raw['Salesman'].dropna().unique().tolist())

        # --- FILTER TIM SALESMAN (MULTI-SELECT UNTUK SS) ---
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👥 **Pilih Salesman (Tim SS)**")
            select_all = st.checkbox("Pilih Semua Salesman (Total Area)", value=True)
            
            if select_all:
                selected_salesmen = st.multiselect("Salesman Terpilih:", options=all_salesmen, default=all_salesmen)
            else:
                selected_salesmen = st.multiselect("Salesman Terpilih:", options=all_salesmen, default=all_salesmen[:3] if len(all_salesmen) >= 3 else all_salesmen)

        if not selected_salesmen:
            st.warning("Silakan pilih minimal 1 salesman pada menu di sebelah kiri.")
            st.stop()

        # Filter data sesuai salesman terpilih
        df = df_raw[df_raw['Salesman'].isin(selected_salesmen)].copy()

        # Agregasi SKU MHS
        df_mhs_tx = df[df['Pcode_Str'].isin(mhs_pcode_set)].copy()
        agg_sku = df_mhs_tx.groupby(['No Outlet', 'Pcode_Str'])['NET_QTY'].sum().reset_index()
        valid_mhs = agg_sku[agg_sku['NET_QTY'] > 0]
        sku_per_toko = valid_mhs.groupby('No Outlet').size().reset_index(name='Realisasi SKU Sold')

        # Database Toko
        base_cols = ['No Outlet', 'Nama Outlet', 'Kode Sales', 'Salesman', 'Channel', 'Kabupaten', 'Kecamatan', 'Kode Pasar']
        cols_exist = [c for c in base_cols if c in df.columns]
        outlet_master = df[cols_exist].drop_duplicates(subset=['No Outlet'])
        calc_toko = pd.merge(outlet_master, sku_per_toko, on='No Outlet', how='left').fillna({'Realisasi SKU Sold': 0})
        calc_toko['Realisasi SKU Sold'] = calc_toko['Realisasi SKU Sold'].astype(int)

        calc_toko['Channel_Prefix'] = calc_toko['Channel'].astype(str).str.slice(0, 3)
        calc_toko['Target SKU'] = calc_toko['Channel_Prefix'].map(DEFAULT_TARGET_CHANNEL).fillna(7).astype(int)
        calc_toko['Status Lolos'] = (calc_toko['Realisasi SKU Sold'] >= calc_toko['Target SKU']).astype(int)
        calc_toko['Gap SKU'] = (calc_toko['Target SKU'] - calc_toko['Realisasi SKU Sold']).apply(lambda x: max(0, x))

        # KPI Makro
        total_ec = len(calc_toko)
        total_lolos_mhs = calc_toko['Status Lolos'].sum()
        ach_cb_standpro = (total_lolos_mhs / cb_standpro) * 100
        
        total_net_sales = df['NET_AMOUNT'].sum()
        total_bruto = df['BRUTO_AMOUNT'].sum()
        total_retur = df['RETUR_AMOUNT'].sum()
        retur_rate = (total_retur / total_bruto * 100) if total_bruto > 0 else 0

        # Tier Insentif
        if ach_cb_standpro >= 80: 
            tier_label = "Tier 4 (≥ 80%) [Maksimal]"
            gauge_color = "#16a34a"
        elif ach_cb_standpro >= 70: 
            tier_label = "Tier 3 (70% - 79.9%)"
            gauge_color = "#0284c7"
        elif ach_cb_standpro >= 60: 
            tier_label = "Tier 2 (60% - 69.9%)"
            gauge_color = "#d97706"
        elif ach_cb_standpro >= 50: 
            tier_label = "Tier 1 (50% - 59.9%)"
            gauge_color = "#ca8a04"
        else: 
            tier_label = "< 50% (Belum Masuk Tier)"
            gauge_color = "#dc2626"

        target_tier1 = int(cb_standpro * 0.5)
        gap_toko_t1 = max(0, target_tier1 - total_lolos_mhs)

        # --- TAMPILAN DASHBOARD ---
        st.title("📊 Monitoring Operasional & Eksekutif Sales (SS / RSM / GRSM)")
        st.caption(f"Cakupan: **{len(selected_salesmen)} Salesman Terpilih** | Target Standpro: **{cb_standpro:,} Toko**")

        # --- LOGIKA DELTA PANAH & PERSENTASE RETUR ---
        is_lolos_tier = ach_cb_standpro >= 50.0

        if total_retur > 0:
            delta_omset = f"-{retur_rate:.2f}% Retur (Bruto Rp {total_bruto:,.0f})"
            delta_color_omset = "normal"  # Panah merah ke bawah
        else:
            delta_omset = f"+0% Retur (Bruto Rp {total_bruto:,.0f})"
            delta_color_omset = "normal"

        if is_lolos_tier:
            delta_mhs = f"+{ach_cb_standpro:.2f}% vs Standpro"
            delta_color_mhs = "normal"   # Panah hijau ke atas
        else:
            delta_mhs = f"-{ach_cb_standpro:.2f}% vs Standpro (Target 50%)"
            delta_color_mhs = "normal"   # Panah merah ke bawah

        if gap_toko_t1 == 0:
            delta_status = "+Target Tier 1 Tercapai"
            delta_color_status = "normal" # Panah hijau ke atas
        else:
            delta_status = f"-Kurang {gap_toko_t1:,} Toko ke Tier 1"
            delta_color_status = "normal" # Panah merah ke bawah

        # --- 4 KARTU METRIK EKSEKUTIF BERBINGKAI ---
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric(
                label="Omset Bersih (Net)",
                value=f"Rp {total_net_sales:,.0f}",
                delta=delta_omset,
                delta_color=delta_color_omset,
                border=True
            )
        with c2:
            st.metric(
                label="Toko Transaksi (EC)",
                value=f"{total_ec:,} Toko",
                delta=f"+{df['Faktur'].nunique():,} Faktur",
                delta_color="normal",
                border=True
            )
        with c3:
            st.metric(
                label="Toko Lolos MHS",
                value=f"{total_lolos_mhs:,} Toko",
                delta=delta_mhs,
                delta_color=delta_color_mhs,
                border=True
            )
        with c4:
            st.metric(
                label="Status Insentif",
                value=tier_label,
                delta=delta_status,
                delta_color=delta_color_status,
                border=True
            )

        st.markdown("---")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Kinerja Salesman & Progress", 
            "📍 Omset & Sebaran Wilayah", 
            "📦 Kontribusi Subbrand & Divisi", 
            "🏬 Analisis Tipe Toko (Channel)", 
            "🎯 Action Plan Toko (Gap MHS)"
        ])

        # TAB 1: KINERJA SALESMAN & CHARTS
        with tab1:
            st.subheader("Pencapaian Insentif & Kinerja Tim")
            cg, cb = st.columns([1, 2])
            
            with cg:
                fig_g = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = ach_cb_standpro,
                    number = {'suffix': "%", 'font': {'size': 26}},
                    title = {'text': "Pencapaian vs Standpro", 'font': {'size': 14}},
                    gauge = {
                        'axis': {'range': [0, 100], 'tickwidth': 1},
                        'bar': {'color': gauge_color},
                        'steps': [
                            {'range': [0, 50], 'color': "#fee2e2"},
                            {'range': [50, 70], 'color': "#fef3c7"},
                            {'range': [70, 80], 'color': "#e0f2fe"},
                            {'range': [80, 100], 'color': "#dcfce7"}
                        ],
                        'threshold': {'line': {'color': "#0f172a", 'width': 3}, 'thickness': 0.75, 'value': 50}
                    }
                ))
                fig_g.update_layout(height=260, margin=dict(l=20, r=20, t=30, b=10))
                st.plotly_chart(fig_g, use_container_width=True)

            with cb:
                chart_df = calc_toko.groupby('Salesman').agg(
                    Covered=('No Outlet', 'count'),
                    Lolos=('Status Lolos', 'sum')
                ).reset_index()
                
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(name='Toko Tercover (EC)', x=chart_df['Salesman'], y=chart_df['Covered'], marker_color='#94a3b8'))
                fig_bar.add_trace(go.Bar(name='Toko Lolos MHS', x=chart_df['Salesman'], y=chart_df['Lolos'], marker_color='#0284c7'))
                fig_bar.update_layout(
                    title="Perbandingan Toko Tercover vs Toko Lolos MHS",
                    height=260,
                    margin=dict(l=10, r=10, t=35, b=10),
                    barmode='group',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("#### Tabel Rincian Kinerja Salesman")
            sales_val = df.groupby(['Kode Sales', 'Salesman']).agg(
                Net_Sales=('NET_AMOUNT', 'sum'),
                Total_Faktur=('Faktur', 'nunique')
            ).reset_index()

            sales_agg = calc_toko.groupby(['Kode Sales', 'Salesman']).agg(
                EC=('No Outlet', 'count'),
                Toko_Lolos_MHS=('Status Lolos', 'sum'),
                Avg_SKU=('Realisasi SKU Sold', 'mean')
            ).reset_index()

            sales_perf = pd.merge(sales_val, sales_agg, on=['Kode Sales', 'Salesman'])
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

        # TAB 2: OMSET & SEBARAN WILAYAH
        with tab2:
            st.subheader("Analisis Penjualan Berdasarkan Wilayah")
            col_kab, col_kec = st.columns(2)

            with col_kab:
                st.markdown("#### Penjualan per Kabupaten")
                kab_val = df.groupby('Kabupaten')['NET_AMOUNT'].sum().reset_index()
                kab_out = calc_toko.groupby('Kabupaten').agg(
                    Total_Toko=('No Outlet', 'count'),
                    Toko_Lolos=('Status Lolos', 'sum')
                ).reset_index()
                kab_merge = pd.merge(kab_val, kab_out, on='Kabupaten').sort_values(by='NET_AMOUNT', ascending=False)
                kab_merge['Kontribusi (%)'] = ((kab_merge['NET_AMOUNT'] / total_net_sales) * 100).round(1)
                kab_merge['Strike Rate (%)'] = ((kab_merge['Toko_Lolos'] / kab_merge['Total_Toko']) * 100).round(1)
                kab_merge['Omset (Rp)'] = kab_merge['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                
                st.dataframe(
                    kab_merge[['Kabupaten', 'Omset (Rp)', 'Kontribusi (%)', 'Total_Toko', 'Toko_Lolos', 'Strike Rate (%)']],
                    use_container_width=True
                )

                fig_kab = px.pie(
                    kab_merge, 
                    names='Kabupaten', 
                    values='NET_AMOUNT', 
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Safe,
                    title="Porsi Omset per Kabupaten"
                )
                fig_kab.update_layout(height=280, margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_kab, use_container_width=True)

            with col_kec:
                st.markdown("#### Top 10 Kecamatan berdasarkan Omset")
                kec_val = df.groupby('Kecamatan')['NET_AMOUNT'].sum().reset_index()
                kec_out = calc_toko.groupby('Kecamatan').agg(
                    Total_Toko=('No Outlet', 'count'),
                    Toko_Lolos=('Status Lolos', 'sum')
                ).reset_index()
                kec_merge = pd.merge(kec_val, kec_out, on='Kecamatan').sort_values(by='NET_AMOUNT', ascending=False).head(10)
                kec_merge['Kontribusi (%)'] = ((kec_merge['NET_AMOUNT'] / total_net_sales) * 100).round(1)
                kec_merge['Strike Rate (%)'] = ((kec_merge['Toko_Lolos'] / kec_merge['Total_Toko']) * 100).round(1)
                kec_merge['Omset (Rp)'] = kec_merge['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")

                st.dataframe(
                    kec_merge[['Kecamatan', 'Omset (Rp)', 'Kontribusi (%)', 'Total_Toko', 'Toko_Lolos', 'Strike Rate (%)']],
                    use_container_width=True
                )

                fig_kec = px.bar(
                    kec_merge.sort_values(by='NET_AMOUNT', ascending=True),
                    x='NET_AMOUNT',
                    y='Kecamatan',
                    orientation='h',
                    labels={'NET_AMOUNT': 'Omset Bersih (Rp)'},
                    color_discrete_sequence=['#0284c7'],
                    title="Grafik Omset Top 10 Kecamatan"
                )
                fig_kec.update_layout(height=280, margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_kec, use_container_width=True)

            if 'Kode Pasar' in df.columns and (df['Kode Pasar'] != '-').any():
                st.markdown("---")
                st.markdown("#### Sebaran Penjualan per Pasar / Rayon")
                pasar_val = df.groupby('Kode Pasar')['NET_AMOUNT'].sum().reset_index()
                pasar_out = calc_toko.groupby('Kode Pasar').agg(
                    Toko_Aktif=('No Outlet', 'count'),
                    Toko_Lolos=('Status Lolos', 'sum')
                ).reset_index()
                pasar_merge = pd.merge(pasar_val, pasar_out, on='Kode Pasar').sort_values(by='NET_AMOUNT', ascending=False).head(15)
                pasar_merge['Omset Bersih (Rp)'] = pasar_merge['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                pasar_merge['Strike Rate (%)'] = ((pasar_merge['Toko_Lolos'] / pasar_merge['Toko_Aktif']) * 100).round(1)
                st.dataframe(pasar_merge[['Kode Pasar', 'Omset Bersih (Rp)', 'Toko_Aktif', 'Toko_Lolos', 'Strike Rate (%)']], use_container_width=True)

        # TAB 3: SUBBRAND & DIVISI
        with tab3:
            st.subheader("Kontribusi Produk & Divisi")
            col_sb1, col_sb2 = st.columns(2)
            
            with col_sb1:
                st.markdown("#### Top 10 Subbrand berdasarkan Omset")
                if 'SUBBRANDNAME' in df.columns:
                    top_sb = df.groupby('SUBBRANDNAME')['NET_AMOUNT'].sum().reset_index().sort_values(by='NET_AMOUNT', ascending=False).head(10)
                    top_sb['Omset (Rp)'] = top_sb['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                    top_sb['Kontribusi (%)'] = ((top_sb['NET_AMOUNT'] / total_net_sales) * 100).round(2)
                    st.dataframe(top_sb[['SUBBRANDNAME', 'Omset (Rp)', 'Kontribusi (%)']], use_container_width=True)

                    fig_pie = px.pie(
                        top_sb.head(6), 
                        names='SUBBRANDNAME', 
                        values='NET_AMOUNT', 
                        hole=0.45,
                        color_discrete_sequence=px.colors.qualitative.Prism,
                        title="Porsi 6 Brand Terbesar"
                    )
                    fig_pie.update_layout(height=260, margin=dict(l=10, r=10, t=35, b=10))
                    st.plotly_chart(fig_pie, use_container_width=True)

            with col_sb2:
                st.markdown("#### Penjualan per Divisi")
                if 'Divisi' in df.columns:
                    div_sales = df.groupby('Divisi')['NET_AMOUNT'].sum().reset_index().sort_values(by='NET_AMOUNT', ascending=False)
                    div_sales['Divisi'] = "Divisi " + div_sales['Divisi'].astype(str)
                    div_sales['Omset (Rp)'] = div_sales['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                    div_sales['Kontribusi (%)'] = ((div_sales['NET_AMOUNT'] / total_net_sales) * 100).round(2)
                    st.dataframe(div_sales[['Divisi', 'Omset (Rp)', 'Kontribusi (%)']], use_container_width=True)

                    fig_div = px.bar(
                        div_sales, 
                        x='Divisi', 
                        y='NET_AMOUNT', 
                        color='Divisi',
                        color_discrete_sequence=px.colors.qualitative.Safe,
                        title="Omset per Divisi"
                    )
                    fig_div.update_layout(height=260, margin=dict(l=10, r=10, t=35, b=10))
                    st.plotly_chart(fig_div, use_container_width=True)

        # TAB 4: CHANNEL & TERRITORY
        with tab4:
            st.subheader("Performa Channel (Tipe Toko)")
            channel_val = df.groupby('Channel')['NET_AMOUNT'].sum().reset_index()
            channel_rep = calc_toko.groupby('Channel').agg(
                Total_EC=('No Outlet', 'count'),
                Toko_Lolos=('Status Lolos', 'sum')
            ).reset_index()
            channel_merge = pd.merge(channel_val, channel_rep, on='Channel').sort_values(by='Total_EC', ascending=False)
            channel_merge['% Lolos Channel'] = ((channel_merge['Toko_Lolos'] / channel_merge['Total_EC']) * 100).round(1)
            channel_merge['Omset (Rp)'] = channel_merge['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
            
            st.dataframe(
                channel_merge[['Channel', 'Total_EC', 'Toko_Lolos', '% Lolos Channel', 'Omset (Rp)']],
                use_container_width=True
            )

            fig_ch = px.bar(
                channel_merge,
                x='Channel',
                y='Total_EC',
                color='% Lolos Channel',
                labels={'Total_EC': 'Jumlah Toko Tercover', '% Lolos Channel': '% Lolos MHS'},
                color_continuous_scale='Blues',
                title="Jumlah Toko Tercover & Kelulusan per Channel"
            )
            fig_ch.update_layout(height=280, margin=dict(l=10, r=10, t=35, b=10))
            st.plotly_chart(fig_ch, use_container_width=True)

        # TAB 5: ACTION PLAN GAP MHS
        with tab5:
            st.subheader("🎯 Action Plan: Toko Belum Lolos (Prioritas Push SKU)")
            sls_options = ['SEMUA TIM SS'] + selected_salesmen
            pilih_sales = st.selectbox("Pilih Salesman:", sls_options)

            df_action = calc_toko if pilih_sales == 'SEMUA TIM SS' else calc_toko[calc_toko['Salesman'] == pilih_sales]
            df_gap = df_action[df_action['Status Lolos'] == 0].sort_values(by=['Gap SKU', 'Realisasi SKU Sold'], ascending=[True, False])

            st.write(f"Ditemukan **{len(df_gap):,}** toko yang belum lolos:")
            cols_gap = ['No Outlet', 'Nama Outlet', 'Salesman', 'Channel', 'Kabupaten', 'Target SKU', 'Realisasi SKU Sold', 'Gap SKU']
            st.dataframe(df_gap[cols_gap], use_container_width=True)

            # Export All Data
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                display_sales.to_excel(writer, sheet_name='PERFORMA_SALESMAN', index=False)
                df_gap[cols_gap].to_excel(writer, sheet_name='GAP_OUTLET_ACTION', index=False)
                kab_merge.to_excel(writer, sheet_name='OMSET_KABUPATEN', index=False)
                calc_toko.to_excel(writer, sheet_name='DATABASE_OUTLET', index=False)

            st.download_button(
                label="📥 Unduh Laporan Lengkap (.xlsx)",
                data=buf.getvalue(),
                file_name="Laporan_Monitoring_Penjualan_MHS.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as err:
        st.error(f"Gagal memproses file LBP: {str(err)}")
else:
    st.info("👈 Silakan upload file **LBP.txt** pada menu sebelah kiri untuk memproses dashboard monitoring.")
