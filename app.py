import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

# 1. Konfigurasi Halaman Web
st.set_page_config(
    page_title="Monitoring Penjualan & Insentif MHS",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Desain Warna Teduh & Lembut (Eye-Friendly Soft Theme)
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * {
            font-family: 'Inter', sans-serif;
        }
        
        /* Background Utama: Abu-abu Sangat Lembut */
        .stApp {
            background-color: #f1f5f9;
            color: #334155;
        }
        
        /* Container Spacing */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        
        /* Header Dashboard */
        .soft-header {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .soft-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #1e293b;
            margin: 0;
        }
        .soft-subtitle {
            font-size: 0.82rem;
            color: #64748b;
            margin-top: 3px;
        }
        
        /* Kartu Metrik Lembut (KPI Cards) */
        .kpi-box {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            padding: 16px 18px;
            margin-bottom: 10px;
        }
        .kpi-title {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #64748b;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .kpi-value {
            font-size: 1.45rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.2;
            margin-bottom: 4px;
        }
        .kpi-sub {
            font-size: 0.78rem;
            color: #64748b;
        }
        
        /* Status Badge Pastel (Tidak Terang Menyolok) */
        .badge-soft {
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 600;
            display: inline-block;
        }
        .badge-green { background-color: #d1fae5; color: #065f46; }
        .badge-amber { background-color: #fef3c7; color: #92400e; }
        .badge-rose  { background-color: #ffe4e6; color: #9f1239; }
        
        /* Tab Navigasi Minimalis */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: transparent;
            border-bottom: 1px solid #cbd5e1;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 0.86rem;
            font-weight: 600;
            color: #64748b;
            padding: 8px 16px;
            background-color: transparent;
            border-radius: 6px 6px 0 0;
        }
        .stTabs [aria-selected="true"] {
            color: #1e293b !important;
            border-bottom: 2px solid #475569 !important;
            background-color: #ffffff;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Master Standar Target Channel & SKU
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
with st.sidebar:
    st.markdown("### **Panel Data**")
    st.caption("Monitoring Kinerja & Insentif Tim")
    st.markdown("---")
    
    cb_standpro = st.number_input(
        "Target Standpro (CB Area):",
        min_value=1,
        value=1090,
        step=50,
        help="Target dasar toko aktif (CB) untuk mengukur persentase pencapaian."
    )
    
    uploaded_lbp = st.file_uploader("Upload LBP (.txt / .csv / .xlsx):", type=['txt', 'csv', 'xlsx'])
    uploaded_mhs = st.file_uploader("Upload Master SKU MHS (Opsional):", type=['csv', 'xlsx'])
    
    st.markdown("---")
    st.caption("Sistem Analitik Distribusi")

# --- PROSES PERHITUNGAN DATA ---
if uploaded_lbp is not None:
    try:
        with st.spinner("Memuat dan menghitung data..."):
            df_raw = parse_raw_lbp(uploaded_lbp)

            # Master MHS
            if uploaded_mhs is not None:
                df_ref = pd.read_excel(uploaded_mhs) if uploaded_mhs.name.endswith('.xlsx') else pd.read_csv(uploaded_mhs)
                mhs_pcode_set = set(df_ref['Pcode'].astype(str).str.strip().unique())
            else:
                mhs_pcode_set = set(DEFAULT_MHS_LIST)

            # Normalisasi
            df_raw['Salesman'] = df_raw['Salesman'].astype(str).str.strip()
            df_raw['Pcode_Str'] = df_raw['Pcode'].astype(str).str.strip()
            df_raw['QTYPCS'] = pd.to_numeric(df_raw['QTYPCS'], errors='coerce').fillna(0)
            df_raw['AMOUNT'] = pd.to_numeric(df_raw['AMOUNT'], errors='coerce').fillna(0)
            df_raw['Kabupaten'] = df_raw['Kabupaten'].fillna('LAINNYA').astype(str).str.strip()
            df_raw['Kecamatan'] = df_raw['Kecamatan'].fillna('LAINNYA').astype(str).str.strip()
            
            is_retur = df_raw['TRANSTYPE'].astype(str).str.strip().str.upper() == 'R'
            df_raw['NET_QTY'] = df_raw['QTYPCS'].where(~is_retur, -df_raw['QTYPCS'])
            df_raw['NET_AMOUNT'] = df_raw['AMOUNT'].where(~is_retur, -df_raw['AMOUNT'])
            df_raw['RETUR_AMOUNT'] = df_raw['AMOUNT'].where(is_retur, 0)
            df_raw['BRUTO_AMOUNT'] = df_raw['AMOUNT'].where(~is_retur, 0)

            all_salesmen = sorted(df_raw['Salesman'].dropna().unique().tolist())

        # Filter Salesman Tim SPV di Sidebar
        with st.sidebar:
            st.markdown("### 👥 **Pilih Tim Salesman**")
            select_all = st.checkbox("Pilih Semua Salesman (Total Area)", value=True)
            
            if select_all:
                selected_salesmen = st.multiselect("Salesman Terpilih:", options=all_salesmen, default=all_salesmen)
            else:
                selected_salesmen = st.multiselect("Salesman Terpilih:", options=all_salesmen, default=all_salesmen[:3] if len(all_salesmen) >= 3 else all_salesmen)

        if not selected_salesmen:
            st.info("Silakan centang atau pilih minimal 1 salesman di panel kiri.")
            st.stop()

        df = df_raw[df_raw['Salesman'].isin(selected_salesmen)].copy()

        # Agregasi SKU MHS (Varian Unik Net Qty > 0)
        df_mhs_tx = df[df['Pcode_Str'].isin(mhs_pcode_set)].copy()
        agg_sku = df_mhs_tx.groupby(['No Outlet', 'Pcode_Str'])['NET_QTY'].sum().reset_index()
        valid_mhs = agg_sku[agg_sku['NET_QTY'] > 0]
        sku_per_toko = valid_mhs.groupby('No Outlet').size().reset_index(name='Realisasi SKU Sold')

        # Database Toko Tercover
        outlet_master = df[['No Outlet', 'Nama Outlet', 'Kode Sales', 'Salesman', 'Channel', 'Kabupaten', 'Kecamatan', 'Kode Pasar']].drop_duplicates(subset=['No Outlet'])
        calc_toko = pd.merge(outlet_master, sku_per_toko, on='No Outlet', how='left').fillna({'Realisasi SKU Sold': 0})
        calc_toko['Realisasi SKU Sold'] = calc_toko['Realisasi SKU Sold'].astype(int)

        calc_toko['Channel_Prefix'] = calc_toko['Channel'].astype(str).str.slice(0, 3)
        calc_toko['Target SKU'] = calc_toko['Channel_Prefix'].map(DEFAULT_TARGET_CHANNEL).fillna(7).astype(int)
        calc_toko['Status Lolos'] = (calc_toko['Realisasi SKU Sold'] >= calc_toko['Target SKU']).astype(int)
        calc_toko['Gap SKU'] = (calc_toko['Target SKU'] - calc_toko['Realisasi SKU Sold']).apply(lambda x: max(0, x))

        # Ringkasan KPI
        total_ec = len(calc_toko)
        total_lolos_mhs = calc_toko['Status Lolos'].sum()
        ach_cb_standpro = (total_lolos_mhs / cb_standpro) * 100
        
        total_net_sales = df['NET_AMOUNT'].sum()
        total_bruto = df['BRUTO_AMOUNT'].sum()
        total_retur = df['RETUR_AMOUNT'].sum()
        retur_rate = (total_retur / total_bruto * 100) if total_bruto > 0 else 0

        # Tier Insentif (Warna Lembut)
        if ach_cb_standpro >= 80: 
            tier_label = "Tier 4 (≥ 80%)"
            badge_class = "badge-green"
            gauge_bar_color = "#059669"
        elif ach_cb_standpro >= 70: 
            tier_label = "Tier 3 (70% - 79.9%)"
            badge_class = "badge-green"
            gauge_bar_color = "#0284c7"
        elif ach_cb_standpro >= 60: 
            tier_label = "Tier 2 (60% - 69.9%)"
            badge_class = "badge-amber"
            gauge_bar_color = "#d97706"
        elif ach_cb_standpro >= 50: 
            tier_label = "Tier 1 (50% - 59.9%)"
            badge_class = "badge-amber"
            gauge_bar_color = "#ca8a04"
        else: 
            tier_label = "Belum Lolos (< 50%)"
            badge_class = "badge-rose"
            gauge_bar_color = "#be123c"

        target_tier1 = int(cb_standpro * 0.5)
        gap_toko_t1 = max(0, target_tier1 - total_lolos_mhs)

        # --- HEADER UTAMA ---
        st.markdown(f"""
        <div class="soft-header">
            <div>
                <h2 class="soft-title">Monitoring Penjualan & Insentif MHS</h2>
                <div class="soft-subtitle">Tim: <b>{len(selected_salesmen)} Salesman Terpilih</b> &bull; Target CB Standpro: <b>{cb_standpro:,} Toko</b></div>
            </div>
            <div>
                <span class="badge-soft {badge_class}">{tier_label}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- KARTU METRIK UTAMA (WARNA NETRAL & TEDUH) ---
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f"""
            <div class="kpi-box">
                <div class="kpi-title">Omset Bersih (Net Sales)</div>
                <div class="kpi-value">Rp {total_net_sales:,.0f}</div>
                <div class="kpi-sub">Bruto: Rp {total_bruto:,.0f} &bull; Retur: {retur_rate:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        with k2:
            st.markdown(f"""
            <div class="kpi-box">
                <div class="kpi-title">Toko Tercover (EC)</div>
                <div class="kpi-value">{total_ec:,} <span style="font-size:0.95rem; color:#64748b; font-weight:500;">Toko</span></div>
                <div class="kpi-sub">Total Faktur: {df['Faktur'].nunique():,} Transaksi</div>
            </div>
            """, unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class="kpi-box">
                <div class="kpi-title">Toko Lolos Target MHS</div>
                <div class="kpi-value" style="color: #0369a1;">{total_lolos_mhs:,} <span style="font-size:0.95rem; color:#64748b; font-weight:500;">Toko</span></div>
                <div class="kpi-sub">Pencapaian: <b>{ach_cb_standpro:.2f}%</b> vs Standpro</div>
            </div>
            """, unsafe_allow_html=True)
        with k4:
            st.markdown(f"""
            <div class="kpi-box">
                <div class="kpi-title">Kekurangan ke Tier 1 (50%)</div>
                <div class="kpi-value" style="color: {'#be123c' if gap_toko_t1 > 0 else '#047857'};">
                    {f"{gap_toko_t1:,} Toko" if gap_toko_t1 > 0 else "Sudah Tercapai"}
                </div>
                <div class="kpi-sub">Target Minimal: {target_tier1:,} Toko Lolos</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

        # --- TAB KONTEN ---
        t1, t2, t3, t4, t5 = st.tabs([
            "Kinerja Salesman", 
            "Omset & Sebaran Wilayah",
            "Produk & Divisi", 
            "Tipe Toko (Channel)", 
            "Daftar Toko Belum Capai Target"
        ])

        # TAB 1: KINERJA SALESMAN
        with t1:
            cg, cb = st.columns([1, 2])
            with cg:
                st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#475569;'>Pencapaian Insentif vs Target Standpro</p>", unsafe_allow_html=True)
                fig_g = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = ach_cb_standpro,
                    number = {'suffix': "%", 'font': {'size': 26, 'color': '#1e293b'}},
                    gauge = {
                        'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#cbd5e1"},
                        'bar': {'color': gauge_bar_color},
                        'bgcolor': "#ffffff",
                        'borderwidth': 1,
                        'bordercolor': "#cbd5e1",
                        'steps': [
                            {'range': [0, 50], 'color': "#f1f5f9"},
                            {'range': [50, 70], 'color': "#e2e8f0"},
                            {'range': [70, 80], 'color': "#cbd5e1"},
                            {'range': [80, 100], 'color': "#94a3b8"}
                        ],
                        'threshold': {'line': {'color': "#334155", 'width': 2}, 'thickness': 0.7, 'value': 50}
                    }
                ))
                fig_g.update_layout(height=230, margin=dict(l=15, r=15, t=5, b=5), paper_bgcolor="#ffffff")
                st.plotly_chart(fig_g, use_container_width=True)

            with cb:
                st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#475569;'>Perbandingan Toko Tercover (EC) vs Toko Lolos MHS</p>", unsafe_allow_html=True)
                chart_df = calc_toko.groupby('Salesman').agg(
                    Covered=('No Outlet', 'count'),
                    Lolos=('Status Lolos', 'sum')
                ).reset_index()
                
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(name='Toko Tercover (EC)', x=chart_df['Salesman'], y=chart_df['Covered'], marker_color='#94a3b8'))
                fig_bar.add_trace(go.Bar(name='Toko Lolos MHS', x=chart_df['Salesman'], y=chart_df['Lolos'], marker_color='#3b82f6'))
                fig_bar.update_layout(
                    height=230,
                    margin=dict(l=5, r=5, t=5, b=5),
                    barmode='group',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    yaxis=dict(gridcolor="#f1f5f9")
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#475569; margin-top: 10px;'>Rincian Kinerja Tim Salesman</p>", unsafe_allow_html=True)
            sales_val = df.groupby(['Kode Sales', 'Salesman']).agg(
                Net_Sales=('NET_AMOUNT', 'sum'),
                Total_Faktur=('Faktur', 'nunique')
            ).reset_index()

            sales_agg = calc_toko.groupby(['Kode Sales', 'Salesman']).agg(
                EC=('No Outlet', 'count'),
                Toko_Lolos=('Status Lolos', 'sum'),
                Avg_SKU=('Realisasi SKU Sold', 'mean')
            ).reset_index()

            matrix_sales = pd.merge(sales_val, sales_agg, on=['Kode Sales', 'Salesman'])
            matrix_sales['Strike_Rate'] = ((matrix_sales['Toko_Lolos'] / matrix_sales['EC']) * 100).round(1)
            matrix_sales['Avg_SKU'] = matrix_sales['Avg_SKU'].round(1)
            matrix_sales['Drop_Size'] = (matrix_sales['Net_Sales'] / matrix_sales['Total_Faktur']).round(0)

            disp_matrix = matrix_sales.copy()
            disp_matrix['Net_Sales (Rp)'] = disp_matrix['Net_Sales'].apply(lambda x: f"Rp {x:,.0f}")
            disp_matrix['Drop_Size (Rp)'] = disp_matrix['Drop_Size'].apply(lambda x: f"Rp {x:,.0f}")
            disp_matrix['Strike Rate (%)'] = disp_matrix['Strike_Rate'].apply(lambda x: f"{x:.1f}%")

            st.dataframe(
                disp_matrix[['Kode Sales', 'Salesman', 'Net_Sales (Rp)', 'EC', 'Toko_Lolos', 'Strike Rate (%)', 'Avg_SKU', 'Drop_Size (Rp)']],
                use_container_width=True
            )

        # TAB 2: OMSET & SEBARAN WILAYAH
        with t2:
            w1, w2 = st.columns(2)
            
            with w1:
                st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#475569;'>Omset & Pemerataan per Kabupaten</p>", unsafe_allow_html=True)
                kab_val = df.groupby('Kabupaten')['NET_AMOUNT'].sum().reset_index()
                kab_out = calc_toko.groupby('Kabupaten').agg(
                    Total_Toko=('No Outlet', 'count'),
                    Toko_Lolos=('Status Lolos', 'sum')
                ).reset_index()
                kab_merge = pd.merge(kab_val, kab_out, on='Kabupaten').sort_values(by='NET_AMOUNT', ascending=False)
                kab_merge['Kontribusi (%)'] = ((kab_merge['NET_AMOUNT'] / total_net_sales) * 100).round(1)
                kab_merge['Strike Rate (%)'] = ((kab_merge['Toko_Lolos'] / kab_merge['Total_Toko']) * 100).round(1)
                kab_merge['Omset Bersih (Rp)'] = kab_merge['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                
                st.dataframe(
                    kab_merge[['Kabupaten', 'Omset Bersih (Rp)', 'Kontribusi (%)', 'Total_Toko', 'Toko_Lolos', 'Strike Rate (%)']],
                    use_container_width=True
                )
                
                # Visualisasi Donut Kabupaten Lembut
                fig_kab = px.pie(
                    kab_merge, 
                    names='Kabupaten', 
                    values='NET_AMOUNT', 
                    hole=0.45,
                    color_discrete_sequence=['#64748b', '#94a3b8', '#cbd5e1', '#e2e8f0']
                )
                fig_kab.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#ffffff")
                st.plotly_chart(fig_kab, use_container_width=True)

            with w2:
                st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#475569;'>Top 10 Kecamatan berdasarkan Penjualan</p>", unsafe_allow_html=True)
                kec_val = df.groupby('Kecamatan')['NET_AMOUNT'].sum().reset_index()
                kec_out = calc_toko.groupby('Kecamatan').agg(
                    Total_Toko=('No Outlet', 'count'),
                    Toko_Lolos=('Status Lolos', 'sum')
                ).reset_index()
                kec_merge = pd.merge(kec_val, kec_out, on='Kecamatan').sort_values(by='NET_AMOUNT', ascending=False).head(10)
                kec_merge['Kontribusi (%)'] = ((kec_merge['NET_AMOUNT'] / total_net_sales) * 100).round(1)
                kec_merge['Strike Rate (%)'] = ((kec_merge['Toko_Lolos'] / kec_merge['Total_Toko']) * 100).round(1)
                kec_merge['Omset Bersih (Rp)'] = kec_merge['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                
                st.dataframe(
                    kec_merge[['Kecamatan', 'Omset Bersih (Rp)', 'Kontribusi (%)', 'Total_Toko', 'Toko_Lolos', 'Strike Rate (%)']],
                    use_container_width=True
                )
                
                # Bar Chart Kecamatan Lembut
                fig_kec = px.bar(
                    kec_merge, 
                    x='Kecamatan', 
                    y='NET_AMOUNT',
                    labels={'NET_AMOUNT': 'Omset (Rp)'},
                    color_discrete_sequence=['#475569']
                )
                fig_kec.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", yaxis=dict(gridcolor="#f1f5f9"))
                st.plotly_chart(fig_kec, use_container_width=True)

            st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#475569; margin-top:10px;'>Sebaran Penjualan per Pasar / Rayon</p>", unsafe_allow_html=True)
            if 'Kode Pasar' in df.columns:
                pasar_val = df.groupby('Kode Pasar')['NET_AMOUNT'].sum().reset_index()
                pasar_out = calc_toko.groupby('Kode Pasar').agg(
                    Toko_Aktif=('No Outlet', 'count'),
                    Toko_Lolos=('Status Lolos', 'sum')
                ).reset_index()
                pasar_merge = pd.merge(pasar_val, pasar_out, on='Kode Pasar').sort_values(by='NET_AMOUNT', ascending=False).head(15)
                pasar_merge['Omset Bersih (Rp)'] = pasar_merge['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                pasar_merge['Strike Rate (%)'] = ((pasar_merge['Toko_Lolos'] / pasar_merge['Toko_Aktif']) * 100).round(1)
                st.dataframe(pasar_merge[['Kode Pasar', 'Omset Bersih (Rp)', 'Toko_Aktif', 'Toko_Lolos', 'Strike Rate (%)']], use_container_width=True)

        # TAB 3: PRODUK & DIVISI
        with t3:
            p1, p2 = st.columns(2)
            with p1:
                st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#475569;'>Top 10 Subbrand berdasarkan Omset</p>", unsafe_allow_html=True)
                if 'SUBBRANDNAME' in df.columns:
                    top_sb = df.groupby('SUBBRANDNAME')['NET_AMOUNT'].sum().reset_index().sort_values(by='NET_AMOUNT', ascending=False).head(10)
                    top_sb['Omset (Rp)'] = top_sb['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                    top_sb['Porsi (%)'] = ((top_sb['NET_AMOUNT'] / total_net_sales) * 100).round(2)
                    st.dataframe(top_sb[['SUBBRANDNAME', 'Omset (Rp)', 'Porsi (%)']], use_container_width=True)

                    fig_sb = px.pie(
                        top_sb.head(6), 
                        names='SUBBRANDNAME', 
                        values='NET_AMOUNT', 
                        hole=0.45,
                        color_discrete_sequence=['#334155', '#475569', '#64748b', '#94a3b8', '#cbd5e1', '#e2e8f0']
                    )
                    fig_sb.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#ffffff")
                    st.plotly_chart(fig_sb, use_container_width=True)

            with p2:
                st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#475569;'>Penjualan Berdasarkan Divisi</p>", unsafe_allow_html=True)
                if 'Divisi' in df.columns:
                    div_df = df.groupby('Divisi')['NET_AMOUNT'].sum().reset_index().sort_values(by='NET_AMOUNT', ascending=False)
                    div_df['Divisi'] = "Divisi " + div_df['Divisi'].astype(str)
                    div_df['Omset (Rp)'] = div_df['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                    div_df['Porsi (%)'] = ((div_df['NET_AMOUNT'] / total_net_sales) * 100).round(2)
                    st.dataframe(div_df[['Divisi', 'Omset (Rp)', 'Porsi (%)']], use_container_width=True)

                    fig_d = px.bar(
                        div_df, 
                        x='Divisi', 
                        y='NET_AMOUNT',
                        color_discrete_sequence=['#475569']
                    )
                    fig_d.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", yaxis=dict(gridcolor="#f1f5f9"))
                    st.plotly_chart(fig_d, use_container_width=True)

        # TAB 4: CHANNEL MIX
        with t4:
            st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#475569;'>Performa Penjualan Berdasarkan Channel Toko</p>", unsafe_allow_html=True)
            ch_val = df.groupby('Channel')['NET_AMOUNT'].sum().reset_index()
            ch_out = calc_toko.groupby('Channel').agg(
                Total_Toko=('No Outlet', 'count'),
                Toko_Lolos=('Status Lolos', 'sum')
            ).reset_index()
            ch_merge = pd.merge(ch_val, ch_out, on='Channel').sort_values(by='Total_Toko', ascending=False)
            ch_merge['Omset (Rp)'] = ch_merge['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
            ch_merge['Strike Rate (%)'] = ((ch_merge['Toko_Lolos'] / ch_merge['Total_Toko']) * 100).round(1)
            
            st.dataframe(
                ch_merge[['Channel', 'Total_Toko', 'Toko_Lolos', 'Strike Rate (%)', 'Omset (Rp)']],
                use_container_width=True
            )

        # TAB 5: ACTION PLAN TOKO BELUM CAPAI TARGET
        with t5:
            st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#475569;'>Daftar Toko Prioritas Dorongan SKU</p>", unsafe_allow_html=True)
            pilih_sales = st.selectbox("Pilih Salesman:", ['SEMUA TIM SPV'] + selected_salesmen)
            
            df_action = calc_toko if pilih_sales == 'SEMUA TIM SPV' else calc_toko[calc_toko['Salesman'] == pilih_sales]
            gap_outlets = df_action[df_action['Status Lolos'] == 0].sort_values(by=['Gap SKU', 'Realisasi SKU Sold'], ascending=[True, False])
            
            st.write(f"Menampilkan **{len(gap_outlets):,}** toko yang belum lolos target:")
            cols_view = ['No Outlet', 'Nama Outlet', 'Salesman', 'Channel', 'Kabupaten', 'Target SKU', 'Realisasi SKU Sold', 'Gap SKU']
            st.dataframe(gap_outlets[cols_view], use_container_width=True)

            # Tombol Download Excel Laporan Lengkap
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                matrix_sales.to_excel(writer, sheet_name='KINERJA_SALESMAN', index=False)
                gap_outlets[cols_view].to_excel(writer, sheet_name='DAFTAR_GAP_TOKO', index=False)
                kab_merge.to_excel(writer, sheet_name='OMSET_KABUPATEN', index=False)
                calc_toko.to_excel(writer, sheet_name='SELURUH_TOKO', index=False)

            st.download_button(
                label="📥 Unduh Laporan Lengkap (.xlsx)",
                data=buf.getvalue(),
                file_name="Laporan_Monitoring_Penjualan_MHS.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Gagal membaca file: {str(e)}")
else:
    st.info("👈 Silakan upload file **LBP.txt** pada panel sebelah kiri untuk memproses dashboard.")
