import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

st.set_page_config(
    page_title="Executive Sales Monitoring | FMCG Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS UNTUK UI MODERN ---
st.markdown("""
    <style>
        .main {
            background-color: #0e1117;
        }
        .metric-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.25);
            margin-bottom: 12px;
        }
        .metric-title {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94a3b8;
            margin-bottom: 4px;
            font-weight: 600;
        }
        .metric-val {
            font-size: 1.6rem;
            font-weight: 700;
            color: #f8fafc;
            margin-bottom: 2px;
        }
        .metric-sub {
            font-size: 0.8rem;
            color: #64748b;
        }
        .badge-success {
            background-color: rgba(34, 197, 94, 0.2);
            color: #4ade80;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-danger {
            background-color: rgba(239, 68, 68, 0.2);
            color: #f87171;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

# Master Konfigurasi
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

# --- SIDEBAR OPERASIONAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=65)
    st.markdown("### **Panel Kontrol Area**")
    st.caption("Monitoring Operasional Salesman & Insentif MHS")
    st.markdown("---")
    
    cb_standpro = st.number_input(
        "🎯 Target Base CB Standpro:",
        min_value=1,
        value=1090,
        step=50,
        help="Target Customer Base Area untuk pembagi persentase kelulusan insentif."
    )
    
    target_sales_rp = st.number_input(
        "💰 Target Omset Sales (Rp, Opsional):",
        min_value=0,
        value=0,
        step=50000000
    )
    
    st.markdown("---")
    uploaded_lbp = st.file_uploader("📥 Upload LBP (.txt / .csv / .xlsx)", type=['txt', 'csv', 'xlsx'])
    uploaded_mhs = st.file_uploader("📋 Custom Master MHS (Opsional)", type=['csv', 'xlsx'])

# --- MAIN DASHBOARD AREA ---
if uploaded_lbp is not None:
    try:
        with st.spinner("⚡ Mengkalkulasi data transaksi dan metriks KPI..."):
            df = parse_raw_lbp(uploaded_lbp)

            # Master MHS
            if uploaded_mhs is not None:
                df_ref = pd.read_excel(uploaded_mhs) if uploaded_mhs.name.endswith('.xlsx') else pd.read_csv(uploaded_mhs)
                mhs_pcode_set = set(df_ref['Pcode'].astype(str).str.strip().unique())
            else:
                mhs_pcode_set = set(DEFAULT_MHS_LIST)

            # Standardisasi Tipe Data
            df['Pcode_Str'] = df['Pcode'].astype(str).str.strip()
            df['QTYPCS'] = pd.to_numeric(df['QTYPCS'], errors='coerce').fillna(0)
            df['AMOUNT'] = pd.to_numeric(df['AMOUNT'], errors='coerce').fillna(0)
            
            # Hitung Faktur vs Retur
            is_retur = df['TRANSTYPE'].astype(str).str.strip().str.upper() == 'R'
            df['NET_QTY'] = df['QTYPCS'].where(~is_retur, -df['QTYPCS'])
            df['NET_AMOUNT'] = df['AMOUNT'].where(~is_retur, -df['AMOUNT'])
            df['RETUR_AMOUNT'] = df['AMOUNT'].where(is_retur, 0)
            df['BRUTO_AMOUNT'] = df['AMOUNT'].where(~is_retur, 0)

            # Evaluasi SKU MHS Outlet Level
            df_mhs_tx = df[df['Pcode_Str'].isin(mhs_pcode_set)].copy()
            agg_sku = df_mhs_tx.groupby(['No Outlet', 'Pcode_Str'])['NET_QTY'].sum().reset_index()
            valid_mhs = agg_sku[agg_sku['NET_QTY'] > 0]
            sku_per_toko = valid_mhs.groupby('No Outlet').size().reset_index(name='Realisasi SKU Sold')

            # Profil Master Toko
            outlet_master = df[['No Outlet', 'Nama Outlet', 'Kode Sales', 'Salesman', 'Channel', 'Kabupaten', 'Kecamatan']].drop_duplicates(subset=['No Outlet'])
            calc_toko = pd.merge(outlet_master, sku_per_toko, on='No Outlet', how='left').fillna({'Realisasi SKU Sold': 0})
            calc_toko['Realisasi SKU Sold'] = calc_toko['Realisasi SKU Sold'].astype(int)

            calc_toko['Channel_Prefix'] = calc_toko['Channel'].astype(str).str.slice(0, 3)
            calc_toko['Target SKU'] = calc_toko['Channel_Prefix'].map(DEFAULT_TARGET_CHANNEL).fillna(7).astype(int)
            calc_toko['Status Lolos'] = (calc_toko['Realisasi SKU Sold'] >= calc_toko['Target SKU']).astype(int)
            calc_toko['Gap SKU'] = (calc_toko['Target SKU'] - calc_toko['Realisasi SKU Sold']).apply(lambda x: max(0, x))

            # Ringkasan KPI Makro
            total_ec = len(calc_toko)
            total_lolos_mhs = calc_toko['Status Lolos'].sum()
            ach_cb_standpro = (total_lolos_mhs / cb_standpro) * 100
            
            total_net_sales = df['NET_AMOUNT'].sum()
            total_bruto = df['BRUTO_AMOUNT'].sum()
            total_retur = df['RETUR_AMOUNT'].sum()
            retur_rate = (total_retur / total_bruto * 100) if total_bruto > 0 else 0

            # Tier Insentif
            if ach_cb_standpro >= 80: 
                tier_label = "Tier 4 (≥ 80%) [MAX]"
                tier_color = "#22c55e"
            elif ach_cb_standpro >= 70: 
                tier_label = "Tier 3 (70% - 79.9%)"
                tier_color = "#06b6d4"
            elif ach_cb_standpro >= 60: 
                tier_label = "Tier 2 (60% - 69.9%)"
                tier_color = "#f59e0b"
            elif ach_cb_standpro >= 50: 
                tier_label = "Tier 1 (50% - 59.9%)"
                tier_color = "#eab308"
            else: 
                tier_label = "< 50% (Belum Lolos Tier)"
                tier_color = "#ef4444"

            gap_toko_t1 = max(0, int(cb_standpro * 0.5) - total_lolos_mhs)

        # Header Title
        st.markdown("<h2 style='margin-bottom:0;'>⚡ Executive Monitoring Dashboard</h2>", unsafe_allow_html=True)
        st.caption(f"Sales Supervision & Incentive Performance Tracker | Base CB Standpro: **{cb_standpro:,}** Toko")
        st.markdown("<br>", unsafe_allow_html=True)

        # Baris Kartu Metrik Modern
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Net Sales Value</div>
                <div class="metric-val">Rp {total_net_sales:,.0f}</div>
                <div class="metric-sub">Gross: Rp {total_bruto:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Customer Covered (EC)</div>
                <div class="metric-val">{total_ec:,} <span style="font-size:1rem; color:#94a3b8;">Toko</span></div>
                <div class="metric-sub">Total Faktur: {df['Faktur'].nunique():,}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Toko Lolos Target MHS</div>
                <div class="metric-val" style="color:#38bdf8;">{total_lolos_mhs:,} <span style="font-size:1rem; color:#94a3b8;">Toko</span></div>
                <div class="metric-sub">Pencapaian: {ach_cb_standpro:.2f}% vs CB</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Status Tier Insentif</div>
                <div class="metric-val" style="color:{tier_color}; font-size:1.35rem;">{tier_label}</div>
                <div class="metric-sub">Gap ke Tier 1 (50%): <b>{gap_toko_t1:,} Toko</b></div>
            </div>
            """, unsafe_allow_html=True)

        # Tabs Navigasi Dashboard
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Area & Sales Performance", 
            "📦 Subbrand & Divisi Mix", 
            "🏬 Channel & Rayon Analytics", 
            "🎯 MHS Gap Action Plan"
        ])

        # TAB 1: AREA & SALES PERFORMANCE
        with tab1:
            col_gauge, col_bar = st.columns([1, 2])
            
            with col_gauge:
                st.markdown("##### 🎯 Progress Menuju Tier Insentif")
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = ach_cb_standpro,
                    number = {'suffix': "%", 'font': {'size': 32}},
                    gauge = {
                        'axis': {'range': [0, 100], 'tickwidth': 1},
                        'bar': {'color': tier_color},
                        'steps': [
                            {'range': [0, 50], 'color': "rgba(239, 68, 68, 0.15)"},
                            {'range': [50, 70], 'color': "rgba(234, 179, 8, 0.15)"},
                            {'range': [70, 80], 'color': "rgba(6, 182, 212, 0.15)"},
                            {'range': [80, 100], 'color': "rgba(34, 197, 94, 0.15)"}
                        ],
                        'threshold': {
                            'line': {'color': "white", 'width': 3},
                            'thickness': 0.75,
                            'value': 50
                        }
                    }
                ))
                fig_gauge.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_gauge, use_container_width=True)

            with col_bar:
                st.markdown("##### 👥 Performa Toko Lolos per Salesman")
                sales_mhs_summary = calc_toko.groupby('Salesman').agg(
                    Toko_Tercover=('No Outlet', 'count'),
                    Toko_Lolos=('Status Lolos', 'sum')
                ).reset_index()
                
                fig_bar = px.bar(
                    sales_mhs_summary,
                    x='Salesman',
                    y=['Toko_Tercover', 'Toko_Lolos'],
                    barmode='group',
                    color_discrete_sequence=['#475569', '#38bdf8'],
                    labels={'value': 'Jumlah Toko', 'variable': 'Kategori'}
                )
                fig_bar.update_layout(height=280, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("##### 📋 Matriks Lengkap Tim Salesman")
            sales_val = df.groupby(['Kode Sales', 'Salesman']).agg(
                Net_Sales=('NET_AMOUNT', 'sum'),
                Total_Faktur=('Faktur', 'nunique')
            ).reset_index()

            sales_agg = calc_toko.groupby(['Kode Sales', 'Salesman']).agg(
                EC=('No Outlet', 'count'),
                Toko_Lolos_MHS=('Status Lolos', 'sum'),
                Avg_SKU=('Realisasi SKU Sold', 'mean')
            ).reset_index()

            sales_table = pd.merge(sales_val, sales_agg, on=['Kode Sales', 'Salesman'])
            sales_table['Strike_Rate'] = ((sales_table['Toko_Lolos_MHS'] / sales_table['EC']) * 100).round(1)
            sales_table['Avg_SKU'] = sales_table['Avg_SKU'].round(1)
            sales_table['Drop_Size'] = (sales_table['Net_Sales'] / sales_table['Total_Faktur']).round(0)

            # Format tampilan
            disp_table = sales_table.copy()
            disp_table['Net_Sales (Rp)'] = disp_table['Net_Sales'].apply(lambda x: f"Rp {x:,.0f}")
            disp_table['Drop_Size (Rp)'] = disp_table['Drop_Size'].apply(lambda x: f"Rp {x:,.0f}")
            disp_table['Strike_Rate (%)'] = disp_table['Strike_Rate'].apply(lambda x: f"{x:.1f}%")

            st.dataframe(
                disp_table[['Kode Sales', 'Salesman', 'Net_Sales (Rp)', 'EC', 'Toko_Lolos_MHS', 'Strike_Rate (%)', 'Avg_SKU', 'Drop_Size (Rp)']],
                use_container_width=True
            )

        # TAB 2: SUBBRAND & DIVISI MIX
        with tab2:
            st.markdown("##### 📦 Kontribusi Omset Produk Fokus")
            col_pie1, col_pie2 = st.columns(2)
            
            with col_pie1:
                if 'SUBBRANDNAME' in df.columns:
                    top_sb = df.groupby('SUBBRANDNAME')['NET_AMOUNT'].sum().reset_index().sort_values(by='NET_AMOUNT', ascending=False).head(8)
                    fig_pie = px.pie(
                        top_sb, 
                        names='SUBBRANDNAME', 
                        values='NET_AMOUNT', 
                        hole=0.45,
                        color_discrete_sequence=px.colors.qualitative.Prism,
                        title="Top 8 Subbrand by Net Sales"
                    )
                    fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_pie, use_container_width=True)

            with col_pie2:
                if 'Divisi' in df.columns:
                    div_data = df.groupby('Divisi')['NET_AMOUNT'].sum().reset_index().sort_values(by='NET_AMOUNT', ascending=False)
                    div_data['Divisi'] = "Divisi " + div_data['Divisi'].astype(str)
                    fig_div = px.bar(
                        div_data, 
                        x='Divisi', 
                        y='NET_AMOUNT',
                        color='Divisi',
                        color_discrete_sequence=px.colors.qualitative.Safe,
                        title="Sales Value per Divisi"
                    )
                    fig_div.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_div, use_container_width=True)

        # TAB 3: CHANNEL & RAYON
        with tab3:
            col_ch1, col_ch2 = st.columns(2)
            with col_ch1:
                st.markdown("##### 🏬 Performa per Channel Toko")
                ch_summary = calc_toko.groupby('Channel').agg(
                    Total_EC=('No Outlet', 'count'),
                    Toko_Lolos=('Status Lolos', 'sum')
                ).reset_index()
                ch_summary['Strike Rate (%)'] = ((ch_summary['Toko_Lolos'] / ch_summary['Total_EC']) * 100).round(1)
                st.dataframe(ch_summary.sort_values(by='Total_EC', ascending=False), use_container_width=True)

            with col_ch2:
                st.markdown("##### 📍 Performa per Wilayah (Kabupaten)")
                if 'Kabupaten' in calc_toko.columns:
                    kab_summary = calc_toko.groupby('Kabupaten').agg(
                        Total_EC=('No Outlet', 'count'),
                        Toko_Lolos=('Status Lolos', 'sum')
                    ).reset_index()
                    kab_summary['Strike Rate (%)'] = ((kab_summary['Toko_Lolos'] / kab_summary['Total_EC']) * 100).round(1)
                    st.dataframe(kab_summary.sort_values(by='Total_EC', ascending=False), use_container_width=True)

        # TAB 4: MHS ACTION PLAN
        with tab4:
            st.markdown("##### 🎯 Prioritas Push SKU (Toko Belum Lolos)")
            sls_filter = ['ALL'] + sorted(calc_toko['Salesman'].dropna().unique().tolist())
            pilih_salesman = st.selectbox("Pilih Salesman:", sls_filter)

            action_data = calc_toko if pilih_salesman == 'ALL' else calc_toko[calc_toko['Salesman'] == pilih_salesman]
            df_action_gap = action_data[action_data['Status Lolos'] == 0].sort_values(by=['Gap SKU', 'Realisasi SKU Sold'], ascending=[True, False])

            st.write(f"Menampilkan **{len(df_action_gap):,}** toko prioritas dorong SKU:")
            kolom_tampil = ['No Outlet', 'Nama Outlet', 'Salesman', 'Channel', 'Target SKU', 'Realisasi SKU Sold', 'Gap SKU']
            st.dataframe(df_action_gap[kolom_tampil], use_container_width=True)

            # Export Excel
            export_buffer = io.BytesIO()
            with pd.ExcelWriter(export_buffer, engine='openpyxl') as writer:
                sales_table.to_excel(writer, sheet_name='SUMMARY_SALESMAN', index=False)
                df_action_gap[kolom_tampil].to_excel(writer, sheet_name='GAP_OUTLET_ACTION', index=False)
                calc_toko.to_excel(writer, sheet_name='ALL_OUTLET_DATA', index=False)

            st.download_button(
                label="📥 Download Action Plan & Report (.xlsx)",
                data=export_buffer.getvalue(),
                file_name="Action_Plan_Monitoring_MHS.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Gagal memproses file LBP: {str(e)}")
else:
    st.info("👈 Silakan upload file **LBP.txt** Anda di panel sebelah kiri untuk menampilkan visual dashboard.")
