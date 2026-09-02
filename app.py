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

# CSS 
st.markdown("""
    <style>
        [data-testid="stMetricValue"] {
            font-size: 1.45rem !important;
            word-break: break-word;
            white-space: normal;
        }
        [data-testid="stMetricDelta"] {
            font-size: 0.82rem !important;
            white-space: normal;
        }
        [data-testid="stMetric"] {
            margin-bottom: 0px !important;
            padding-bottom: 0px !important;
        }
        .metric-subtext {
            font-size: 0.78rem;
            color: #94a3b8;
            margin-top: -8px !important;
            padding-bottom: 4px;
        }
        .outlet-card {
            background-color: #f8fafc;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 14px 18px;
            margin-bottom: 15px;
        }
    </style>
""", unsafe_allow_html=True)

# Master Target SKU per Channel
DEFAULT_TARGET_CHANNEL = {
    '111': 7,   # Kios / Retail Small
    '154': 7,   # Wet Retail
    '113': 10,  # Retail Large
    '114': 15,  # Semi Grosir
    '115': 15,  # Grosir Kelontong
    '110': 25   # Grosir Modern / Supermarket
}

# Fungsi Penomoran Mulai dari 1
def beri_nomor_urut(df_target):
    df_res = df_target.copy().reset_index(drop=True)
    df_res.insert(0, 'No', range(1, len(df_res) + 1))
    return df_res

# Parser LBP
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
st.sidebar.markdown("**Akses:** SS / HOA MV42")

cb_standpro = st.sidebar.number_input(
    "Target Standpro (CB Area):",
    min_value=1,
    value=1090,
    step=25,
    help="Target Base Customer (CB) Standpro area untuk menghitung % pencapaian dan tier insentif."
)

uploaded_lbp = st.sidebar.file_uploader("📂 Upload File LBP (.txt / .csv / .xlsx)", type=['txt', 'csv', 'xlsx'])

# --- PEMROSESAN DATA & DASHBOARD ---
if uploaded_lbp is not None:
    try:
        with st.spinner("Memproses data LBP & menghitung total SKU masuk..."):
            df_raw = parse_raw_lbp(uploaded_lbp)

            # Standardisasi Tipe Data
            df_raw['Salesman'] = df_raw['Salesman'].astype(str).str.strip()
            df_raw['Pcode_Str'] = df_raw['Pcode'].astype(str).str.strip()
            df_raw['QTYPCS'] = pd.to_numeric(df_raw['QTYPCS'], errors='coerce').fillna(0)
            df_raw['AMOUNT'] = pd.to_numeric(df_raw['AMOUNT'], errors='coerce').fillna(0)

            if 'Kabupaten' not in df_raw.columns: df_raw['Kabupaten'] = '-'
            else: df_raw['Kabupaten'] = df_raw['Kabupaten'].fillna('-').astype(str).str.strip()

            if 'Kecamatan' not in df_raw.columns: df_raw['Kecamatan'] = '-'
            else: df_raw['Kecamatan'] = df_raw['Kecamatan'].fillna('-').astype(str).str.strip()

            if 'Kode Pasar' not in df_raw.columns: df_raw['Kode Pasar'] = '-'
            else: df_raw['Kode Pasar'] = df_raw['Kode Pasar'].fillna('-').astype(str).str.strip()
            
            is_retur = df_raw['TRANSTYPE'].astype(str).str.strip().str.upper() == 'R'
            df_raw['NET_QTY'] = df_raw['QTYPCS'].where(~is_retur, -df_raw['QTYPCS'])
            df_raw['NET_AMOUNT'] = df_raw['AMOUNT'].where(~is_retur, -df_raw['AMOUNT'])
            df_raw['RETUR_AMOUNT'] = df_raw['AMOUNT'].where(is_retur, 0)
            df_raw['BRUTO_AMOUNT'] = df_raw['AMOUNT'].where(~is_retur, 0)

            all_salesmen = sorted(df_raw['Salesman'].dropna().unique().tolist())

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

        df = df_raw[df_raw['Salesman'].isin(selected_salesmen)].copy()

        base_cols = ['No Outlet', 'Nama Outlet', 'Kode Sales', 'Salesman', 'Channel', 'Kabupaten', 'Kecamatan', 'Kode Pasar']
        cols_exist = [c for c in base_cols if c in df.columns]
        outlet_master = df[cols_exist].drop_duplicates(subset=['No Outlet']).copy()
        outlet_master['Channel_Prefix'] = outlet_master['Channel'].astype(str).str.slice(0, 3)

        # Hitung Total SKU Unik Masuk (Net Qty > 0) per Toko
        outlet_sku_agg = df.groupby(['No Outlet', 'Pcode_Str'])['NET_QTY'].sum().reset_index()
        outlet_sku_positive = outlet_sku_agg[outlet_sku_agg['NET_QTY'] > 0]
        sku_count_per_toko = outlet_sku_positive.groupby('No Outlet')['Pcode_Str'].nunique().reset_index(name='Realisasi SKU Sold')

        calc_toko = pd.merge(outlet_master, sku_count_per_toko, on='No Outlet', how='left').fillna({'Realisasi SKU Sold': 0})
        calc_toko['Realisasi SKU Sold'] = calc_toko['Realisasi SKU Sold'].astype(int)

        calc_toko['Target SKU'] = calc_toko['Channel_Prefix'].map(DEFAULT_TARGET_CHANNEL).fillna(7).astype(int)
        calc_toko['Status Lolos'] = (calc_toko['Realisasi SKU Sold'] >= calc_toko['Target SKU']).astype(int)
        calc_toko['Gap SKU'] = (calc_toko['Target SKU'] - calc_toko['Realisasi SKU Sold']).apply(lambda x: max(0, x))

        total_ec = len(calc_toko)
        total_lolos_mhs = calc_toko['Status Lolos'].sum()
        ach_cb_standpro = (total_lolos_mhs / cb_standpro) * 100
        
        total_net_sales = df['NET_AMOUNT'].sum()
        total_bruto = df['BRUTO_AMOUNT'].sum()
        total_retur = df['RETUR_AMOUNT'].sum()
        retur_rate = (total_retur / total_bruto * 100) if total_bruto > 0 else 0

        if ach_cb_standpro >= 80: 
            tier_label = "Tier 4 (≥ 80%)"
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
            tier_label = "Belum Masuk Tier"
            gauge_color = "#dc2626"

        target_tier1 = int(cb_standpro * 0.5)
        gap_toko_t1 = max(0, target_tier1 - total_lolos_mhs)

        # Header Utama
        st.title("📊 Monitoring Operasional & MHS Area (SS / HOA MV42)")
        st.caption(f"Cakupan: **{len(selected_salesmen)} Salesman Terpilih** | Target Standpro: **{cb_standpro:,} Toko**")

        is_lolos_tier = ach_cb_standpro >= 50.0

        if total_retur > 0:
            delta_omset = f"-{retur_rate:.2f}% Retur"
            delta_color_omset = "normal"
        else:
            delta_omset = "+0.00% Retur"
            delta_color_omset = "normal"

        if is_lolos_tier:
            delta_mhs = f"+{ach_cb_standpro:.2f}% (Target 50%)"
            delta_color_mhs = "normal"
        else:
            delta_mhs = f"-{ach_cb_standpro:.2f}% (Target 50%)"
            delta_color_mhs = "normal"

        if gap_toko_t1 == 0:
            delta_status = "+Tier 1 Tercapai"
            delta_color_status = "normal"
        else:
            delta_status = f"-Kurang {gap_toko_t1:,} Toko"
            delta_color_status = "normal"

        # Kartu Metrik
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            with st.container(border=True):
                st.metric("Omset Bersih (Net)", f"Rp {total_net_sales:,.0f}", delta=delta_omset, delta_color=delta_color_omset)
                st.markdown(f"<div class='metric-subtext'>Bruto: Rp {total_bruto:,.0f}</div>", unsafe_allow_html=True)
        with c2:
            with st.container(border=True):
                st.metric("Toko Transaksi (EC)", f"{total_ec:,} Toko", delta=f"+{df['Faktur'].nunique():,} Faktur", delta_color="normal")
                st.markdown(f"<div class='metric-subtext'>Total Faktur Terbit</div>", unsafe_allow_html=True)
        with c3:
            with st.container(border=True):
                st.metric("Toko Lolos MHS", f"{total_lolos_mhs:,} Toko", delta=delta_mhs, delta_color=delta_color_mhs)
                st.markdown(f"<div class='metric-subtext'>Target Base: {cb_standpro:,} Toko</div>", unsafe_allow_html=True)
        with c4:
            with st.container(border=True):
                st.metric("Status Insentif", tier_label, delta=delta_status, delta_color=delta_color_status)
                st.markdown(f"<div class='metric-subtext'>Target Min Tier 1: {target_tier1:,} Toko</div>", unsafe_allow_html=True)

        st.markdown("---")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Kinerja Salesman", 
            "📍 Omset & Wilayah", 
            "📦 Subbrand & Divisi", 
            "🏬 Tipe Toko (Channel)", 
            "🎯 Action Plan Toko"
        ])

        # TAB 1: KINERJA SALESMAN
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
                fig_bar.update_layout(height=260, margin=dict(l=10, r=10, t=35, b=10), barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("#### Tabel Rincian Kinerja Salesman")
            sales_val = df.groupby(['Kode Sales', 'Salesman']).agg(Net_Sales=('NET_AMOUNT', 'sum'), Total_Faktur=('Faktur', 'nunique')).reset_index()
            sales_agg = calc_toko.groupby(['Kode Sales', 'Salesman']).agg(EC=('No Outlet', 'count'), Toko_Lolos_MHS=('Status Lolos', 'sum'), Avg_SKU=('Realisasi SKU Sold', 'mean')).reset_index()
            sales_perf = pd.merge(sales_val, sales_agg, on=['Kode Sales', 'Salesman'])
            sales_perf['% Strike Rate MHS'] = ((sales_perf['Toko_Lolos_MHS'] / sales_perf['EC']) * 100).round(1)
            sales_perf['Drop Size / Faktur'] = (sales_perf['Net_Sales'] / sales_perf['Total_Faktur']).round(0)
            sales_perf['Avg_SKU'] = sales_perf['Avg_SKU'].round(1)

            display_sales = sales_perf.copy()
            display_sales['Net_Sales (Rp)'] = display_sales['Net_Sales'].apply(lambda x: f"Rp {x:,.0f}")
            display_sales['Drop Size / Faktur'] = display_sales['Drop Size / Faktur'].apply(lambda x: f"Rp {x:,.0f}")
            display_sales['% Strike Rate MHS'] = display_sales['% Strike Rate MHS'].apply(lambda x: f"{x:.1f}%")

            tbl_sales = beri_nomor_urut(display_sales[['Kode Sales', 'Salesman', 'Net_Sales (Rp)', 'EC', 'Toko_Lolos_MHS', '% Strike Rate MHS', 'Avg_SKU', 'Drop Size / Faktur']])
            st.dataframe(tbl_sales, use_container_width=True, hide_index=True)

        # TAB 2: OMSET & WILAYAH
        with tab2:
            st.subheader("Analisis Penjualan Berdasarkan Wilayah")
            col_kab, col_kec = st.columns(2)
            with col_kab:
                st.markdown("#### Penjualan per Kabupaten")
                kab_val = df.groupby('Kabupaten')['NET_AMOUNT'].sum().reset_index()
                kab_out = calc_toko.groupby('Kabupaten').agg(Total_Toko=('No Outlet', 'count'), Toko_Lolos=('Status Lolos', 'sum')).reset_index()
                kab_merge = pd.merge(kab_val, kab_out, on='Kabupaten').sort_values(by='NET_AMOUNT', ascending=False)
                kab_merge['Kontribusi (%)'] = ((kab_merge['NET_AMOUNT'] / total_net_sales) * 100).round(1)
                kab_merge['Strike Rate (%)'] = ((kab_merge['Toko_Lolos'] / kab_merge['Total_Toko']) * 100).round(1)
                kab_merge['Omset (Rp)'] = kab_merge['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                
                tbl_kab = beri_nomor_urut(kab_merge[['Kabupaten', 'Omset (Rp)', 'Kontribusi (%)', 'Total_Toko', 'Toko_Lolos', 'Strike Rate (%)']])
                st.dataframe(tbl_kab, use_container_width=True, hide_index=True)

                fig_kab = px.pie(kab_merge, names='Kabupaten', values='NET_AMOUNT', hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe, title="Porsi Omset per Kabupaten")
                fig_kab.update_layout(height=280, margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_kab, use_container_width=True)

            with col_kec:
                st.markdown("#### Top 10 Kecamatan berdasarkan Omset")
                kec_val = df.groupby('Kecamatan')['NET_AMOUNT'].sum().reset_index()
                kec_out = calc_toko.groupby('Kecamatan').agg(Total_Toko=('No Outlet', 'count'), Toko_Lolos=('Status Lolos', 'sum')).reset_index()
                kec_merge = pd.merge(kec_val, kec_out, on='Kecamatan').sort_values(by='NET_AMOUNT', ascending=False).head(10)
                kec_merge['Kontribusi (%)'] = ((kec_merge['NET_AMOUNT'] / total_net_sales) * 100).round(1)
                kec_merge['Strike Rate (%)'] = ((kec_merge['Toko_Lolos'] / kec_merge['Total_Toko']) * 100).round(1)
                kec_merge['Omset (Rp)'] = kec_merge['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")

                tbl_kec = beri_nomor_urut(kec_merge[['Kecamatan', 'Omset (Rp)', 'Kontribusi (%)', 'Total_Toko', 'Toko_Lolos', 'Strike Rate (%)']])
                st.dataframe(tbl_kec, use_container_width=True, hide_index=True)

                fig_kec = px.bar(kec_merge.sort_values(by='NET_AMOUNT', ascending=True), x='NET_AMOUNT', y='Kecamatan', orientation='h', labels={'NET_AMOUNT': 'Omset Bersih (Rp)'}, color_discrete_sequence=['#0284c7'], title="Grafik Omset Top 10 Kecamatan")
                fig_kec.update_layout(height=280, margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_kec, use_container_width=True)

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
                    tbl_sb = beri_nomor_urut(top_sb[['SUBBRANDNAME', 'Omset (Rp)', 'Kontribusi (%)']])
                    st.dataframe(tbl_sb, use_container_width=True, hide_index=True)

                    fig_pie = px.pie(top_sb.head(6), names='SUBBRANDNAME', values='NET_AMOUNT', hole=0.45, color_discrete_sequence=px.colors.qualitative.Prism, title="Porsi 6 Brand Terbesar")
                    fig_pie.update_layout(height=260, margin=dict(l=10, r=10, t=35, b=10))
                    st.plotly_chart(fig_pie, use_container_width=True)

            with col_sb2:
                st.markdown("#### Penjualan per Divisi")
                if 'Divisi' in df.columns:
                    div_sales = df.groupby('Divisi')['NET_AMOUNT'].sum().reset_index().sort_values(by='NET_AMOUNT', ascending=False)
                    div_sales['Divisi'] = "Divisi " + div_sales['Divisi'].astype(str)
                    div_sales['Omset (Rp)'] = div_sales['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                    div_sales['Kontribusi (%)'] = ((div_sales['NET_AMOUNT'] / total_net_sales) * 100).round(2)
                    tbl_div = beri_nomor_urut(div_sales[['Divisi', 'Omset (Rp)', 'Kontribusi (%)']])
                    st.dataframe(tbl_div, use_container_width=True, hide_index=True)

                    fig_div = px.bar(div_sales, x='Divisi', y='NET_AMOUNT', color='Divisi', color_discrete_sequence=px.colors.qualitative.Safe, title="Omset per Divisi")
                    fig_div.update_layout(height=260, margin=dict(l=10, r=10, t=35, b=10))
                    st.plotly_chart(fig_div, use_container_width=True)

        # TAB 4: CHANNEL & TERRITORY
        with tab4:
            st.subheader("Performa Channel (Tipe Toko)")
            channel_val = df.groupby('Channel')['NET_AMOUNT'].sum().reset_index()
            channel_rep = calc_toko.groupby('Channel').agg(Total_EC=('No Outlet', 'count'), Toko_Lolos=('Status Lolos', 'sum')).reset_index()
            channel_merge = pd.merge(channel_val, channel_rep, on='Channel').sort_values(by='Total_EC', ascending=False)
            channel_merge['% Lolos Channel'] = ((channel_merge['Toko_Lolos'] / channel_merge['Total_EC']) * 100).round(1)
            channel_merge['Omset (Rp)'] = channel_merge['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
            
            tbl_channel = beri_nomor_urut(channel_merge[['Channel', 'Total_EC', 'Toko_Lolos', '% Lolos Channel', 'Omset (Rp)']])
            st.dataframe(tbl_channel, use_container_width=True, hide_index=True)

            fig_ch = px.bar(channel_merge, x='Channel', y='Total_EC', color='% Lolos Channel', labels={'Total_EC': 'Jumlah Toko Tercover', '% Lolos Channel': '% Lolos MHS'}, color_continuous_scale='Blues', title="Jumlah Toko Tercover & Kelulusan per Channel")
            fig_ch.update_layout(height=280, margin=dict(l=10, r=10, t=35, b=10))
            st.plotly_chart(fig_ch, use_container_width=True)

        # TAB 5: ACTION PLAN GAP MHS
        with tab5:
            st.subheader("🎯 Action Plan: Toko Belum Lolos & Detail SKU Masuk")
            sls_options = ['SEMUA TIM SS'] + selected_salesmen
            pilih_sales = st.selectbox("Filter Berdasarkan Salesman:", sls_options)

            df_action = calc_toko if pilih_sales == 'SEMUA TIM SS' else calc_toko[calc_toko['Salesman'] == pilih_sales]
            gap_outlets = df_action[df_action['Status Lolos'] == 0].sort_values(by=['Gap SKU', 'Realisasi SKU Sold'], ascending=[True, False])

            st.write(f"Ditemukan **{len(gap_outlets):,}** toko yang belum lolos target:")
            cols_gap = ['No Outlet', 'Nama Outlet', 'Salesman', 'Channel', 'Kabupaten', 'Target SKU', 'Realisasi SKU Sold', 'Gap SKU']
            
            tbl_gap = beri_nomor_urut(gap_outlets[cols_gap])
            st.dataframe(tbl_gap, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### 🔍 **Pemeriksaan Detail SKU Toko**")
            st.caption("Pilih salah satu toko di bawah untuk melihat rincian SKU yang SUDAH masuk dan yang BELUM masuk:")

            if len(gap_outlets) > 0:
                gap_outlets['Pilihan_Label'] = gap_outlets['No Outlet'].astype(str) + " - " + gap_outlets['Nama Outlet'] + " (Kurang " + gap_outlets['Gap SKU'].astype(str) + " SKU | " + gap_outlets['Salesman'] + ")"
                outlet_options = gap_outlets['Pilihan_Label'].tolist()
                
                selected_outlet_label = st.selectbox("Pilih Toko untuk Melihat Detail SKU:", outlet_options)
                selected_no_outlet = int(selected_outlet_label.split(" - ")[0])

                toko_info = gap_outlets[gap_outlets['No Outlet'] == selected_no_outlet].iloc[0]
                
                st.markdown(f"""
                <div class="outlet-card">
                    <h4 style="margin:0; color:#0f172a;">🏪 {toko_info['Nama Outlet']} (No: {toko_info['No Outlet']})</h4>
                    <p style="margin:4px 0 0 0; font-size:0.85rem; color:#475569;">
                        Salesman: <b>{toko_info['Salesman']}</b> | Channel: <b>{toko_info['Channel']}</b> | Wilayah: <b>{toko_info['Kabupaten']}</b><br>
                        Target Channel: <b>{toko_info['Target SKU']} SKU</b> | Sudah Masuk: <b style="color:#0284c7;">{toko_info['Realisasi SKU Sold']} SKU</b> | 
                        Kekurangan: <b style="color:#dc2626;">{toko_info['Gap SKU']} SKU Lagi</b>
                    </p>
                </div>
                """, unsafe_allow_html=True)

                # Ambil semua SKU unik yang dibeli toko ini dengan net qty > 0
                df_outlet_tx = df[(df['No Outlet'] == selected_no_outlet) & (df['NET_QTY'] > 0)]
                sku_toko_masuk = df_outlet_tx[['Pcode_Str', 'Nama Produk', 'NET_QTY']].drop_duplicates(subset=['Pcode_Str'])
                sku_toko_masuk = sku_toko_masuk.rename(columns={'Pcode_Str': 'Pcode', 'NET_QTY': 'Total Qty Terbeli'})

                st.markdown(f"#### ✅ Rincian SKU yang SUDAH Masuk ({len(sku_toko_masuk)} SKU Varian)")
                if len(sku_toko_masuk) > 0:
                    st.dataframe(beri_nomor_urut(sku_toko_masuk[['Pcode', 'Nama Produk', 'Total Qty Terbeli']]), use_container_width=True, hide_index=True)
                else:
                    st.info("Belum ada SKU yang terbeli di toko ini.")
            else:
                st.success("🎉 Seluruh toko yang tercover sudah lolos target SKU!")

            st.markdown("---")

            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                display_sales.to_excel(writer, sheet_name='PERFORMA_SALESMAN', index=False)
                gap_outlets[cols_gap].to_excel(writer, sheet_name='GAP_OUTLET_ACTION', index=False)
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
