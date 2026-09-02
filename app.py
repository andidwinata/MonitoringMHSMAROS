import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

# 1. Konfigurasi Halaman Enterprise
st.set_page_config(
    page_title="Sales Performance & Incentive Monitoring Portal",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Corporate Theme & Styling (Power BI / Tableau Style)
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Container Utama */
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2rem;
            padding-left: 2.5rem;
            padding-right: 2.5rem;
        }
        
        /* Header Banner Korporat */
        .corp-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 14px;
            margin-bottom: 24px;
        }
        .corp-title {
            font-size: 1.45rem;
            font-weight: 700;
            color: #0f172a;
            letter-spacing: -0.02em;
            margin: 0;
        }
        .corp-subtitle {
            font-size: 0.84rem;
            color: #64748b;
            margin: 4px 0 0 0;
        }
        
        /* Kartu Metrik Eksekutif */
        .kpi-container {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 18px 20px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            height: 100%;
        }
        .kpi-container:hover {
            box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.08);
        }
        .kpi-tag {
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #64748b;
            margin-bottom: 6px;
        }
        .kpi-number {
            font-size: 1.65rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.2;
            margin-bottom: 4px;
        }
        .kpi-footer {
            font-size: 0.76rem;
            color: #64748b;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        /* Status Badge */
        .pill-badge {
            display: inline-block;
            padding: 3px 10px;
            font-size: 0.75rem;
            font-weight: 600;
            border-radius: 9999px;
        }
        .pill-emerald { background-color: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
        .pill-amber { background-color: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
        .pill-red { background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
        
        /* Tab Navigation */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
            border-bottom: 2px solid #f1f5f9;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 0.88rem;
            font-weight: 600;
            color: #64748b;
            padding: 8px 14px 12px 14px;
        }
        .stTabs [aria-selected="true"] {
            color: #0f172a !important;
            border-bottom-color: #0284c7 !important;
        }
    </style>
""", unsafe_allow_html=True)

# Master Data Target & SKU Standar
DEFAULT_TARGET_CHANNEL = {
    '111': 7, '154': 7, '113': 10, '114': 15, '115': 15, '110': 25
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

# --- SIDEBAR OPERASIONAL KORPORAT ---
with st.sidebar:
    st.markdown("### **Operational Parameters**")
    st.caption("Commercial Distribution Management System")
    st.markdown("---")
    
    cb_standpro = st.number_input(
        "Area Base Standpro (Target CB):",
        min_value=1,
        value=1090,
        step=50,
        help="Target dasar Customer Base outlet terdaftar untuk evaluasi pencapaian insentif tim."
    )
    
    uploaded_lbp = st.file_uploader("Upload Laporan Buku Penjualan (.txt / .csv / .xlsx):", type=['txt', 'csv', 'xlsx'])
    uploaded_mhs = st.file_uploader("Master Reference Must Have SKU (Opsional):", type=['csv', 'xlsx'])
    
    st.markdown("---")
    st.markdown("<small style='color:#94a3b8;'>Enterprise BI Engine v2.4<br>Automated LBP Analytics</small>", unsafe_allow_html=True)

# --- ENGINE PEMROSESAN DATA ---
if uploaded_lbp is not None:
    try:
        with st.spinner("Processing transaction data..."):
            df_raw = parse_raw_lbp(uploaded_lbp)

            # Master MHS
            if uploaded_mhs is not None:
                df_ref = pd.read_excel(uploaded_mhs) if uploaded_mhs.name.endswith('.xlsx') else pd.read_csv(uploaded_mhs)
                mhs_pcode_set = set(df_ref['Pcode'].astype(str).str.strip().unique())
            else:
                mhs_pcode_set = set(DEFAULT_MHS_LIST)

            # Standardisasi & Pembersihan Data
            df_raw['Salesman'] = df_raw['Salesman'].astype(str).str.strip()
            df_raw['Pcode_Str'] = df_raw['Pcode'].astype(str).str.strip()
            df_raw['QTYPCS'] = pd.to_numeric(df_raw['QTYPCS'], errors='coerce').fillna(0)
            df_raw['AMOUNT'] = pd.to_numeric(df_raw['AMOUNT'], errors='coerce').fillna(0)
            
            is_retur = df_raw['TRANSTYPE'].astype(str).str.strip().str.upper() == 'R'
            df_raw['NET_QTY'] = df_raw['QTYPCS'].where(~is_retur, -df_raw['QTYPCS'])
            df_raw['NET_AMOUNT'] = df_raw['AMOUNT'].where(~is_retur, -df_raw['AMOUNT'])
            df_raw['RETUR_AMOUNT'] = df_raw['AMOUNT'].where(is_retur, 0)
            df_raw['BRUTO_AMOUNT'] = df_raw['AMOUNT'].where(~is_retur, 0)

            all_salesmen = sorted(df_raw['Salesman'].dropna().unique().tolist())

        # Filter Tim Salesman di Sidebar
        with st.sidebar:
            st.markdown("### **Sales Team Filter**")
            select_all = st.checkbox("Select All Salesman (Macro Area)", value=True)
            
            if select_all:
                selected_salesmen = st.multiselect("Sales Force Portfolio:", options=all_salesmen, default=all_salesmen)
            else:
                selected_salesmen = st.multiselect("Sales Force Portfolio:", options=all_salesmen, default=all_salesmen[:3] if len(all_salesmen) >= 3 else all_salesmen)

        if not selected_salesmen:
            st.info("Pilih minimal 1 salesman pada menu di panel kiri untuk menampilkan performa tim.")
            st.stop()

        df = df_raw[df_raw['Salesman'].isin(selected_salesmen)].copy()

        # Agregasi MHS (Varian Unik Net Qty > 0)
        df_mhs_tx = df[df['Pcode_Str'].isin(mhs_pcode_set)].copy()
        agg_sku = df_mhs_tx.groupby(['No Outlet', 'Pcode_Str'])['NET_QTY'].sum().reset_index()
        valid_mhs = agg_sku[agg_sku['NET_QTY'] > 0]
        sku_per_toko = valid_mhs.groupby('No Outlet').size().reset_index(name='Realisasi SKU Sold')

        # Database Toko
        outlet_master = df[['No Outlet', 'Nama Outlet', 'Kode Sales', 'Salesman', 'Channel', 'Kabupaten', 'Kecamatan']].drop_duplicates(subset=['No Outlet'])
        calc_toko = pd.merge(outlet_master, sku_per_toko, on='No Outlet', how='left').fillna({'Realisasi SKU Sold': 0})
        calc_toko['Realisasi SKU Sold'] = calc_toko['Realisasi SKU Sold'].astype(int)

        calc_toko['Channel_Prefix'] = calc_toko['Channel'].astype(str).str.slice(0, 3)
        calc_toko['Target SKU'] = calc_toko['Channel_Prefix'].map(DEFAULT_TARGET_CHANNEL).fillna(7).astype(int)
        calc_toko['Status Lolos'] = (calc_toko['Realisasi SKU Sold'] >= calc_toko['Target SKU']).astype(int)
        calc_toko['Gap SKU'] = (calc_toko['Target SKU'] - calc_toko['Realisasi SKU Sold']).apply(lambda x: max(0, x))

        # Metrik Agregat
        total_ec = len(calc_toko)
        total_lolos_mhs = calc_toko['Status Lolos'].sum()
        ach_cb_standpro = (total_lolos_mhs / cb_standpro) * 100
        
        total_net_sales = df['NET_AMOUNT'].sum()
        total_bruto = df['BRUTO_AMOUNT'].sum()
        total_retur = df['RETUR_AMOUNT'].sum()
        retur_rate = (total_retur / total_bruto * 100) if total_bruto > 0 else 0

        # Status Tier
        if ach_cb_standpro >= 80: 
            tier_label = "Tier 4 (Max Tier)"
            pill_class = "pill-emerald"
            gauge_color = "#059669"
        elif ach_cb_standpro >= 70: 
            tier_label = "Tier 3 (70% - 79.9%)"
            pill_class = "pill-emerald"
            gauge_color = "#0284c7"
        elif ach_cb_standpro >= 60: 
            tier_label = "Tier 2 (60% - 69.9%)"
            pill_class = "pill-amber"
            gauge_color = "#d97706"
        elif ach_cb_standpro >= 50: 
            tier_label = "Tier 1 (50% - 59.9%)"
            pill_class = "pill-amber"
            gauge_color = "#eab308"
        else: 
            tier_label = "Below Tier (< 50%)"
            pill_class = "pill-red"
            gauge_color = "#dc2626"

        gap_toko_t1 = max(0, int(cb_standpro * 0.5) - total_lolos_mhs)

        # --- HEADER KORPORAT ---
        st.markdown(f"""
        <div class="corp-header">
            <div>
                <h1 class="corp-title">Commercial Sales Performance & Incentive Portal</h1>
                <p class="corp-subtitle">Distribution Coverage & Must Have SKU Realization | Scope: <b>{len(selected_salesmen)} Salesman Portfolio</b></p>
            </div>
            <div>
                <span class="pill-badge {pill_class}">{tier_label}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- BARIS KPI METRIK EKSEKUTIF ---
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-tag">Total Net Revenue</div>
                <div class="kpi-number">Rp {total_net_sales:,.0f}</div>
                <div class="kpi-footer">Gross Rp {total_bruto:,.0f} &bull; Retur {retur_rate:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
        with k2:
            st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-tag">Active Outlets (EC)</div>
                <div class="kpi-number">{total_ec:,} <span style="font-size:1.1rem; color:#64748b; font-weight:500;">Outlets</span></div>
                <div class="kpi-footer">Across {df['Faktur'].nunique():,} Invoices Processed</div>
            </div>
            """, unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-tag">Qualified MHS Outlets</div>
                <div class="kpi-number" style="color:#0284c7;">{total_lolos_mhs:,} <span style="font-size:1.1rem; color:#64748b; font-weight:500;">Outlets</span></div>
                <div class="kpi-footer"><b>{ach_cb_standpro:.2f}%</b> Achievement vs CB Standpro</div>
            </div>
            """, unsafe_allow_html=True)
        with k4:
            st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-tag">Tier 1 Gap Analysis</div>
                <div class="kpi-number" style="color: {'#dc2626' if gap_toko_t1 > 0 else '#059669'};">
                    {f"{gap_toko_t1:,} Toko" if gap_toko_t1 > 0 else "Qualified"}
                </div>
                <div class="kpi-footer">Target Min. Tier 1: {int(cb_standpro * 0.5):,} Outlets</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- TAB STRUKTUR PROFESIONAL ---
        t1, t2, t3, t4 = st.tabs([
            "Executive Dashboard", 
            "Sales Force Matrix", 
            "Brand & Division Portfolio", 
            "Action Plan Outlets"
        ])

        # TAB 1: EXECUTIVE DASHBOARD
        with t1:
            c_gauge, c_trend = st.columns([1, 2])
            
            with c_gauge:
                st.markdown("<p style='font-size:0.9rem; font-weight:600; color:#334155;'>% Achievement vs CB Target</p>", unsafe_allow_html=True)
                fig_g = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = ach_cb_standpro,
                    number = {'suffix': "%", 'font': {'size': 28, 'color': '#0f172a', 'family': 'Inter'}},
                    gauge = {
                        'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#94a3b8"},
                        'bar': {'color': gauge_color},
                        'bgcolor': "#f8fafc",
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
                fig_g.update_layout(height=260, margin=dict(l=20, r=20, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_g, use_container_width=True)

            with c_trend:
                st.markdown("<p style='font-size:0.9rem; font-weight:600; color:#334155;'>Qualified vs Covered Outlets per Salesman</p>", unsafe_allow_html=True)
                perf_chart_df = calc_toko.groupby('Salesman').agg(Covered=('No Outlet', 'count'), Qualified=('Status Lolos', 'sum')).reset_index()
                
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(
                    name='Covered (EC)', 
                    x=perf_chart_df['Salesman'], 
                    y=perf_chart_df['Covered'], 
                    marker_color='#94a3b8'
                ))
                fig_bar.add_trace(go.Bar(
                    name='Qualified MHS', 
                    x=perf_chart_df['Salesman'], 
                    y=perf_chart_df['Qualified'], 
                    marker_color='#0284c7'
                ))
                fig_bar.update_layout(
                    height=260,
                    margin=dict(l=10, r=10, t=10, b=10),
                    barmode='group',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(gridcolor="#f1f5f9")
                )
                st.plotly_chart(fig_bar, use_container_width=True)

        # TAB 2: SALES FORCE MATRIX
        with t2:
            st.markdown("<p style='font-size:0.9rem; font-weight:600; color:#334155;'>Commercial Productivity Table</p>", unsafe_allow_html=True)
            sales_val = df.groupby(['Kode Sales', 'Salesman']).agg(
                Net_Sales=('NET_AMOUNT', 'sum'),
                Total_Faktur=('Faktur', 'nunique')
            ).reset_index()

            sales_agg = calc_toko.groupby(['Kode Sales', 'Salesman']).agg(
                EC=('No Outlet', 'count'),
                Toko_Lolos=('Status Lolos', 'sum'),
                Avg_SKU=('Realisasi SKU Sold', 'mean')
            ).reset_index()

            sf_matrix = pd.merge(sales_val, sales_agg, on=['Kode Sales', 'Salesman'])
            sf_matrix['Strike_Rate'] = ((sf_matrix['Toko_Lolos'] / sf_matrix['EC']) * 100).round(1)
            sf_matrix['Drop_Size'] = (sf_matrix['Net_Sales'] / sf_matrix['Total_Faktur']).round(0)
            sf_matrix['Avg_SKU'] = sf_matrix['Avg_SKU'].round(1)

            display_matrix = sf_matrix.copy()
            display_matrix['Net_Sales (IDR)'] = display_matrix['Net_Sales'].apply(lambda x: f"Rp {x:,.0f}")
            display_matrix['Drop_Size (IDR)'] = display_matrix['Drop_Size'].apply(lambda x: f"Rp {x:,.0f}")
            display_matrix['Strike Rate'] = display_matrix['Strike_Rate'].apply(lambda x: f"{x:.1f}%")

            st.dataframe(
                display_matrix[['Kode Sales', 'Salesman', 'Net_Sales (IDR)', 'EC', 'Toko_Lolos', 'Strike Rate', 'Avg_SKU', 'Drop_Size (IDR)']],
                use_container_width=True
            )

        # TAB 3: BRAND & DIVISION PORTFOLIO
        with t3:
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.markdown("<p style='font-size:0.9rem; font-weight:600; color:#334155;'>Top 8 Subbrands by Revenue Contribution</p>", unsafe_allow_html=True)
                if 'SUBBRANDNAME' in df.columns:
                    top_sb = df.groupby('SUBBRANDNAME')['NET_AMOUNT'].sum().reset_index().sort_values(by='NET_AMOUNT', ascending=False).head(8)
                    fig_p = px.pie(
                        top_sb, 
                        names='SUBBRANDNAME', 
                        values='NET_AMOUNT', 
                        hole=0.55,
                        color_discrete_sequence=px.colors.qualitative.Prism
                    )
                    fig_p.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_p, use_container_width=True)

            with col_b2:
                st.markdown("<p style='font-size:0.9rem; font-weight:600; color:#334155;'>Revenue Distribution by Division</p>", unsafe_allow_html=True)
                if 'Divisi' in df.columns:
                    div_df = df.groupby('Divisi')['NET_AMOUNT'].sum().reset_index().sort_values(by='NET_AMOUNT', ascending=False)
                    div_df['Divisi'] = "Divisi " + div_df['Divisi'].astype(str)
                    fig_d = px.bar(
                        div_df, 
                        x='Divisi', 
                        y='NET_AMOUNT', 
                        color_discrete_sequence=['#0f766e']
                    )
                    fig_d.update_layout(
                        height=300, 
                        margin=dict(l=10, r=10, t=10, b=10), 
                        paper_bgcolor="rgba(0,0,0,0)", 
                        plot_bgcolor="rgba(0,0,0,0)",
                        yaxis=dict(gridcolor="#f1f5f9")
                    )
                    st.plotly_chart(fig_d, use_container_width=True)

        # TAB 4: ACTION PLAN OUTLETS
        with t4:
            st.markdown("<p style='font-size:0.9rem; font-weight:600; color:#334155;'>Target Gap Push List (Unqualified Outlets)</p>", unsafe_allow_html=True)
            
            pilih_rep = st.selectbox("Filter Outlet Berdasarkan Salesman:", ['ALL PORTFOLIO'] + selected_salesmen)
            
            df_action = calc_toko if pilih_rep == 'ALL PORTFOLIO' else calc_toko[calc_toko['Salesman'] == pilih_rep]
            gap_outlets = df_action[df_action['Status Lolos'] == 0].sort_values(by=['Gap SKU', 'Realisasi SKU Sold'], ascending=[True, False])
            
            cols_show = ['No Outlet', 'Nama Outlet', 'Salesman', 'Channel', 'Target SKU', 'Realisasi SKU Sold', 'Gap SKU']
            st.dataframe(gap_outlets[cols_show], use_container_width=True)

            # Export Laporan Excel
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                sf_matrix.to_excel(writer, sheet_name='SALES_PERFORMANCE', index=False)
                gap_outlets[cols_show].to_excel(writer, sheet_name='GAP_OUTLETS_ACTION', index=False)
                calc_toko.to_excel(writer, sheet_name='ALL_OUTLET_RAW', index=False)

            st.download_button(
                label="📥 Export Comprehensive Report (.xlsx)",
                data=buf.getvalue(),
                file_name="Commercial_Sales_Incentive_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Error reading dataset: {str(e)}")
else:
    st.info("👈 Silakan upload file data transaksi mentah (LBP.txt) pada menu di panel sebelah kiri untuk memulai komputasi laporan.")
