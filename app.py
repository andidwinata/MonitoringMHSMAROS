import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

# 1. Konfigurasi Halaman Web
st.set_page_config(
    page_title="Portal Monitoring Penjualan & Insentif MHS",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Desain Tampilan Terang & Bersih (Clean Corporate Theme)
st.markdown("""
    <style>
        /* Latar Belakang & Font */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        
        * {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Background Utama Putih Lembut */
        .stApp {
            background-color: #f8fafc;
            color: #1e293b;
        }
        
        /* Container Spacing */
        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2.5rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        
        /* Header Dashboard */
        .corp-header {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .corp-title {
            font-size: 1.4rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0;
            letter-spacing: -0.02em;
        }
        .corp-subtitle {
            font-size: 0.85rem;
            color: #64748b;
            margin-top: 4px;
        }
        
        /* Kartu Metrik (KPI Tiles) */
        .metric-card {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 18px 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
            margin-bottom: 12px;
            border-top: 4px solid #0284c7;
        }
        .metric-title {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            font-weight: 700;
            margin-bottom: 6px;
        }
        .metric-value {
            font-size: 1.6rem;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.2;
            margin-bottom: 4px;
        }
        .metric-desc {
            font-size: 0.8rem;
            color: #64748b;
        }
        
        /* Status Badge Insentif */
        .badge-status {
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 700;
            display: inline-block;
        }
        .badge-green { background-color: #dcfce7; color: #15803d; border: 1px solid #86efac; }
        .badge-yellow { background-color: #fef9c3; color: #a16207; border: 1px solid #fde047; }
        .badge-red { background-color: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
        
        /* Tab Navigasi */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            background-color: transparent;
            border-bottom: 2px solid #e2e8f0;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 0.9rem;
            font-weight: 600;
            color: #64748b;
            padding: 10px 18px;
            background-color: transparent;
        }
        .stTabs [aria-selected="true"] {
            color: #0284c7 !important;
            border-bottom: 2px solid #0284c7 !important;
            background-color: #ffffff;
            border-radius: 8px 8px 0 0;
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
    st.markdown("### ⚙️ **Pengaturan Data**")
    st.caption("Monitoring Operasional Sales & Insentif")
    st.markdown("---")
    
    cb_standpro = st.number_input(
        "Target Base CB Standpro:",
        min_value=1,
        value=1090,
        step=50,
        help="Target dasar toko aktif (CB) untuk menghitung % pencapaian dan tier insentif."
    )
    
    uploaded_lbp = st.file_uploader("Upload LBP Mentah (.txt / .csv / .xlsx):", type=['txt', 'csv', 'xlsx'])
    uploaded_mhs = st.file_uploader("Upload Master MHS Tambahan (Opsional):", type=['csv', 'xlsx'])
    
    st.markdown("---")
    st.caption("Sistem Analitik LBP Distribusi FMCG")

# --- ENGINE PEMROSESAN UTAMA ---
if uploaded_lbp is not None:
    try:
        with st.spinner("Sedang memproses data dan menghitung seluruh metriks..."):
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
            
            is_retur = df_raw['TRANSTYPE'].astype(str).str.strip().str.upper() == 'R'
            df_raw['NET_QTY'] = df_raw['QTYPCS'].where(~is_retur, -df_raw['QTYPCS'])
            df_raw['NET_AMOUNT'] = df_raw['AMOUNT'].where(~is_retur, -df_raw['AMOUNT'])
            df_raw['RETUR_AMOUNT'] = df_raw['AMOUNT'].where(is_retur, 0)
            df_raw['BRUTO_AMOUNT'] = df_raw['AMOUNT'].where(~is_retur, 0)

            all_salesmen = sorted(df_raw['Salesman'].dropna().unique().tolist())

        # Filter Salesman Tim SPV di Sidebar
        with st.sidebar:
            st.markdown("### 👥 **Filter Tim Salesman (SPV)**")
            select_all = st.checkbox("Pilih Semua Salesman (Total Area)", value=True)
            
            if select_all:
                selected_salesmen = st.multiselect("Daftar Salesman Terpilih:", options=all_salesmen, default=all_salesmen)
            else:
                selected_salesmen = st.multiselect("Daftar Salesman Terpilih:", options=all_salesmen, default=all_salesmen[:3] if len(all_salesmen) >= 3 else all_salesmen)

        if not selected_salesmen:
            st.info("Pilih minimal 1 salesman pada menu sebelah kiri untuk menampilkan data.")
            st.stop()

        df = df_raw[df_raw['Salesman'].isin(selected_salesmen)].copy()

        # Agregasi Must Have SKU (Distinct SKU per toko, Net Qty > 0)
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

        # Penentuan Tier Insentif
        if ach_cb_standpro >= 80: 
            tier_label = "Tier 4 (≥ 80%) - Insentif Maksimal"
            badge_class = "badge-green"
            gauge_color = "#16a34a"
        elif ach_cb_standpro >= 70: 
            tier_label = "Tier 3 (70% - 79.9%)"
            badge_class = "badge-green"
            gauge_color = "#0284c7"
        elif ach_cb_standpro >= 60: 
            tier_label = "Tier 2 (60% - 69.9%)"
            badge_class = "badge-yellow"
            gauge_color = "#d97706"
        elif ach_cb_standpro >= 50: 
            tier_label = "Tier 1 (50% - 59.9%)"
            badge_class = "badge-yellow"
            gauge_color = "#eab308"
        else: 
            tier_label = "Belum Masuk Tier (< 50%)"
            badge_class = "badge-red"
            gauge_color = "#dc2626"

        target_tier1 = int(cb_standpro * 0.5)
        gap_toko_t1 = max(0, target_tier1 - total_lolos_mhs)

        # --- HEADER UTAMA ---
        st.markdown(f"""
        <div class="corp-header">
            <div>
                <h1 class="corp-title">Laporan Monitoring Kinerja Penjualan & Insentif</h1>
                <p class="corp-subtitle">Filter Tim: <b>{len(selected_salesmen)} Salesman Aktif</b> &bull; Target CB Standpro: <b>{cb_standpro:,} Toko</b></p>
            </div>
            <div>
                <span class="badge-status {badge_class}">{tier_label}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- 4 KARTU METRIK UTAMA ---
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Total Omset Bersih</div>
                <div class="metric-value">Rp {total_net_sales:,.0f}</div>
                <div class="metric-desc">Bruto: Rp {total_bruto:,.0f} | Retur: {retur_rate:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
        with k2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Toko Tercover (EC)</div>
                <div class="metric-value">{total_ec:,} <span style="font-size:1rem; color:#64748b; font-weight:600;">Toko</span></div>
                <div class="metric-desc">Dari {df['Faktur'].nunique():,} Faktur Penjualan</div>
            </div>
            """, unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class="metric-card" style="border-top-color: #0284c7;">
                <div class="metric-title">Toko Lolos Target MHS</div>
                <div class="metric-value" style="color:#0284c7;">{total_lolos_mhs:,} <span style="font-size:1rem; color:#64748b; font-weight:600;">Toko</span></div>
                <div class="metric-desc">Pencapaian: <b>{ach_cb_standpro:.2f}%</b> vs Standpro</div>
            </div>
            """, unsafe_allow_html=True)
        with k4:
            st.markdown(f"""
            <div class="metric-card" style="border-top-color: {'#dc2626' if gap_toko_t1 > 0 else '#16a34a'};">
                <div class="metric-title">Kekurangan ke Tier 1 (50%)</div>
                <div class="metric-value" style="color: {'#dc2626' if gap_toko_t1 > 0 else '#16a34a'};">
                    {f"{gap_toko_t1:,} Toko" if gap_toko_t1 > 0 else "Tercapai"}
                </div>
                <div class="metric-desc">Target Minimal Tier 1: {target_tier1:,} Toko</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- TAB NAVIGASI ---
        t1, t2, t3, t4, t5 = st.tabs([
            "📊 Kinerja Tim Salesman", 
            "📍 Omset & Sebaran Wilayah",
            "📦 Kontribusi Produk & Divisi", 
            "🏬 Analisis Tipe Toko (Channel)", 
            "🎯 Daftar Toko Belum Capai Target"
        ])

        # TAB 1: KINERJA SALESMAN
        with t1:
            cg, cb = st.columns([1, 2])
            with cg:
                st.markdown("##### 🎯 Pencapaian vs Target CB")
                fig_g = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = ach_cb_standpro,
                    number = {'suffix': "%", 'font': {'size': 30, 'color': '#0f172a'}},
                    gauge = {
                        'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#94a3b8"},
                        'bar': {'color': gauge_color},
                        'bgcolor': "#ffffff",
                        'borderwidth': 1,
                        'bordercolor': "#e2e8f0",
                        'steps': [
                            {'range': [0, 50], 'color': "#fee2e2"},
                            {'range': [50, 70], 'color': "#fef3c7"},
                            {'range': [70, 80], 'color': "#e0f2fe"},
                            {'range': [80, 100], 'color': "#dcfce7"}
                        ],
                        'threshold': {'line': {'color': "#0f172a", 'width': 3}, 'thickness': 0.75, 'value': 50}
                    }
                ))
                fig_g.update_layout(height=260, margin=dict(l=15, r=15, t=10, b=10), paper_bgcolor="#ffffff")
                st.plotly_chart(fig_g, use_container_width=True)

            with cb:
                st.markdown("##### 👥 Jumlah Toko Tercover vs Toko Lolos MHS")
                chart_df = calc_toko.groupby('Salesman').agg(
                    Covered=('No Outlet', 'count'),
                    Lolos=('Status Lolos', 'sum')
                ).reset_index()
                
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(name='Toko Tercover (EC)', x=chart_df['Salesman'], y=chart_df['Covered'], marker_color='#94a3b8'))
                fig_bar.add_trace(go.Bar(name='Toko Lolos MHS', x=chart_df['Salesman'], y=chart_df['Lolos'], marker_color='#0284c7'))
                fig_bar.update_layout(
                    height=260,
                    margin=dict(l=10, r=10, t=10, b=10),
                    barmode='group',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    yaxis=dict(gridcolor="#f1f5f9")
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("##### 📋 Tabel Rekap Kinerja Salesman")
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

        # TAB 2: OMSET & SEBARAN WILAYAH (LENGKAP)
        with t2:
            st.markdown("##### 📍 Analisis Penjualan Berdasarkan Wilayah & Rayon")
            w1, w2 = st.columns(2)
            
            with w1:
                st.markdown("**1. Omset & Toko per Kabupaten:**")
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
                
                # Visualisasi Donut Kabupaten
                fig_kab = px.pie(
                    kab_merge, 
                    names='Kabupaten', 
                    values='NET_AMOUNT', 
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Safe,
                    title="Porsi Omset per Kabupaten"
                )
                fig_kab.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#ffffff")
                st.plotly_chart(fig_kab, use_container_width=True)

            with w2:
                st.markdown("**2. Top 10 Kecamatan dengan Penjualan Tertinggi:**")
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
                
                # Bar Chart Kecamatan
                fig_kec = px.bar(
                    kec_merge, 
                    x='Kecamatan', 
                    y='NET_AMOUNT',
                    labels={'NET_AMOUNT': 'Omset Bersih (Rp)'},
                    color_discrete_sequence=['#0284c7'],
                    title="Grafik Omset Top 10 Kecamatan"
                )
                fig_kec.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#ffffff", plot_bgcolor="#ffffff")
                st.plotly_chart(fig_kec, use_container_width=True)

            st.markdown("---")
            st.markdown("**3. Sebaran Penjualan per Pasar / Rayon:**")
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
                st.markdown("##### 📦 Top 10 Subbrand berdasarkan Omset")
                if 'SUBBRANDNAME' in df.columns:
                    top_sb = df.groupby('SUBBRANDNAME')['NET_AMOUNT'].sum().reset_index().sort_values(by='NET_AMOUNT', ascending=False).head(10)
                    top_sb['Omset (Rp)'] = top_sb['NET_AMOUNT'].apply(lambda x: f"Rp {x:,.0f}")
                    top_sb['Porsi (%)'] = ((top_sb['NET_AMOUNT'] / total_net_sales) * 100).round(2)
                    st.dataframe(top_sb[['SUBBRANDNAME', 'Omset (Rp)', 'Porsi (%)']], use_container_width=True)

                    fig_sb = px.pie(
                        top_sb.head(6), 
                        names='SUBBRANDNAME', 
                        values='NET_AMOUNT', 
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Prism,
                        title="Porsi 6 Brand Terbesar"
                    )
                    fig_sb.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#ffffff")
                    st.plotly_chart(fig_sb, use_container_width=True)

            with p2:
                st.markdown("##### 🏢 Penjualan per Divisi")
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
                        color='Divisi',
                        color_discrete_sequence=px.colors.qualitative.Safe,
                        title="Omset per Divisi"
                    )
                    fig_d.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#ffffff", plot_bgcolor="#ffffff")
                    st.plotly_chart(fig_d, use_container_width=True)

        # TAB 4: CHANNEL MIX
        with t4:
            st.markdown("##### 🏬 Performa Penjualan Berdasarkan Channel (Tipe Toko)")
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
            st.markdown("##### 🎯 Prioritas Kunjungan: Toko yang Belum Capai Target SKU")
            pilih_sales = st.selectbox("Pilih Salesman:", ['SEMUA TIM SPV'] + selected_salesmen)
            
            df_action = calc_toko if pilih_sales == 'SEMUA TIM SPV' else calc_toko[calc_toko['Salesman'] == pilih_sales]
            gap_outlets = df_action[df_action['Status Lolos'] == 0].sort_values(by=['Gap SKU', 'Realisasi SKU Sold'], ascending=[True, False])
            
            st.write(f"Ditemukan **{len(gap_outlets):,}** toko yang tinggal butuh dorongan SKU tambahan:")
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
        st.error(f"Gagal memproses file LBP: {str(e)}")
else:
    st.info("👈 Silakan upload file data mentah **LBP.txt** pada panel sebelah kiri untuk menampilkan dashboard laporan.")
