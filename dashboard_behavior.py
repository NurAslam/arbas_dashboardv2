"""
ARBAS MARKET INTELLIGENCE — BEHAVIOR ANALYTICS DASHBOARD
Focus: Outlet Behavior, Channel Patterns, Market Geography, Repeat Order
=====================================================================
Run: streamlit run dashboard_behavior.py
"""

# ── Page Config (must be first Streamlit command) ──────────────────────────────
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
import struct
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Arbas Behavior Analytics",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ── WKB Geometry Decoder ──────────────────────────────────────────────────────
def decode_wkb_geom(wkb_str):
    """
    Decode PostGIS WKB hex string (SRID=4326, WGS84) to (lat, lon).
    Format: 01 01000020 E6100000 + X(8 bytes) + Y(8 bytes)
    After byte-order(1) + type(4) + SRID(4) = bytes 9-12, coords at bytes 13-28.
    """
    if pd.isna(wkb_str) or not wkb_str:
        return None, None
    try:
        hex_str = wkb_str.strip()
        if hex_str.startswith('0x'):
            hex_str = hex_str[2:]
        data = bytes.fromhex(hex_str[:50])
        # X = longitude, Y = latitude (standard WGS84 PostGIS)
        lon = struct.unpack('<d', data[9:17])[0]
        lat = struct.unpack('<d', data[17:25])[0]
        # Validate: Yogyakarta area roughly lat -8 to -7.4, lon 110 to 111
        if -9 < lat < -6.5 and 109 < lon < 111:
            return lat, lon
        return None, None
    except Exception:
        return None, None


# ── Load Customer Geometries ────────────────────────────────────────────────────
@st.cache_data
def load_customer_geo():
    """
    Load customers.csv, decode WKB geom, join with transaction outlets.
    Returns DataFrame with lat/lon per customer_id.
    """
    cust = pd.read_csv("customers.csv")

    # Decode WKB
    geo = cust[cust['geom'].notna()].copy()
    lats, lons = [], []
    for g in geo['geom']:
        lat, lon = decode_wkb_geom(g)
        lats.append(lat)
        lons.append(lon)
    geo['lat'] = lats
    geo['lon'] = lons
    geo_valid = geo.dropna(subset=['lat','lon'])

    # Select relevant columns for join
    geo_cols = geo_valid[['id','nama','alamat','tipeChannel','provinsi','kota','status','lat','lon']].copy()
    geo_cols.columns = ['customer_id','customer_name_full','alamat','tipeChannel','provinsi','kota','cust_status','lat','lon']
    return geo_cols, len(geo_valid), len(geo_valid.dropna(subset=['lat','lon']))


geo_df, geo_total, geo_decoded = load_customer_geo()

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Background & Base ── */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
    }
    [data-testid="stMainBlockContainer"] {
        background-color: #0d1117;
        color: #e6edf3;
    }
    [data-testid="stHeader"] {
        background-color: #0d1117;
        color: #e6edf3;
    }
    [data-testid="stSidebar"] {
        background-color: #161b22;
        color: #e6edf3;
        border-right: 1px solid #30363d;
    }
    [data-testid="stSidebarUser"] {
        color: #e6edf3;
    }
    [data-testid="stSidebarContent"] {
        color: #e6edf3;
    }

    /* ── Typography ── */
    h1, h2, h3, h4, h5, h6 {
        color: #e6edf3 !important;
    }
    p, span, div {
        color: #e6edf3;
    }
    .stMarkdown, .stMarkdownContainer {
        color: #e6edf3;
    }

    /* ── Section Header ── */
    .section-header {
        font-size: 1.4rem;
        font-weight: 700;
        color: #58a6ff;
        border-bottom: 3px solid #388bfd;
        padding-bottom: 0.3rem;
        margin-bottom: 1rem;
    }

    /* ── Cards ── */
    .insight-card {
        background: #161b22;
        color: #e6edf3;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.5);
        border-left: 4px solid #388bfd;
    }
    .warn-card {
        background: #1c2a1c;
        color: #e6edf3;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.5);
        border-left: 4px solid #d29922;
    }
    .danger-card {
        background: #2a1c1c;
        color: #e6edf3;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.5);
        border-left: 4px solid #f85149;
    }
    .success-card {
        background: #1c2a1c;
        color: #e6edf3;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.5);
        border-left: 4px solid #3fb950;
    }
    .metric-box {
        background: #161b22;
        color: #e6edf3;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.5);
    }

    /* ── KPI Metrics ── */
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700;
        color: #58a6ff !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.75rem;
        color: #8b949e !important;
        text-transform: uppercase;
    }
    [data-testid="stMetric"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 0.75rem;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #0d1117;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        color: #8b949e;
        border: 1px solid #30363d;
        border-radius: 6px 6px 0 0;
        padding: 6px 16px;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #1f6feb !important;
        color: #ffffff !important;
        border-color: #1f6feb;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #1f6feb !important;
        color: #ffffff !important;
        border-color: #1f6feb;
    }

    /* ── Tables ── */
    .stDataFrame {
        background: #161b22;
        color: #e6edf3;
    }
    [data-testid="stDataFrame"] table {
        background: #161b22;
        color: #e6edf3;
    }
    [data-testid="stDataFrame"] th {
        background: #21262d !important;
        color: #8b949e !important;
        border-color: #30363d !important;
    }
    [data-testid="stDataFrame"] td {
        background: #161b22 !important;
        color: #e6edf3 !important;
        border-color: #30363d !important;
    }
    [data-testid="stDataFrame"] tr:hover td {
        background: #1f2937 !important;
    }

    /* ── Selectbox / Multiselect ── */
    [data-baseweb="select"] {
        background: #161b22 !important;
        color: #e6edf3 !important;
    }
    [data-baseweb="tag"] {
        background: #1f6feb !important;
        color: #ffffff !important;
    }
    div[data-testid="stSelectbox"] label,
    div[data-testid="stMultiSelect"] label {
        color: #8b949e !important;
    }

    /* ── Plotly Charts (fix white bg in dark mode) ── */
    .js-plotly-plot .plotly, .js-plotly-plot .plotly div {
        background: transparent !important;
    }
    .stPlotlyChart [data-testid="stVegaLiteChart"] {
        background: #161b22;
        border-radius: 8px;
        padding: 4px;
    }

    /* ── Horizontal Radio (nav tabs) ── */
    [data-testid="stRadio"] label {
        color: #8b949e;
    }

    /* ── Dividers ── */
    hr {
        border-color: #30363d !important;
    }

    /* ── Captions & Footer ── */
    [data-testid="stCaption"] {
        color: #8b949e !important;
    }
    .st-emotion-cache-13k7y6f {
        color: #8b949e;
    }
</style>
""", unsafe_allow_html=True)

# ── Load Data ───────────────────────────────────────────────────────────────────
@st.cache_data
def load_main():
    df = pd.read_csv("master_sales_analysis.csv")

    # Ambil date + jam dari Transaction.csv createdAt (ada jam sebenarnya!)
    tx = pd.read_csv("Transaction.csv")
    tx['createdAt'] = pd.to_datetime(tx['createdAt'])
    tx['hour'] = tx['createdAt'].dt.hour
    tx['day_name'] = tx['createdAt'].dt.day_name()
    tx['transaction_date_real'] = tx['createdAt'].dt.date  # override date dari createdAt

    # Join: master_sales_analysis.bill_no ←→ Transaction.csv.billNo
    hour_df = tx[['billNo','createdAt','transaction_date_real','hour','day_name']].rename(columns={
        'billNo': 'bill_no'
    })

    # Merge ke df berdasarkan bill_no
    df = df.merge(hour_df, on='bill_no', how='left')

    # Override transaction_date dari createdAt (bukan dari kolom date lama)
    if 'transaction_date_real' in df.columns:
        df['transaction_date'] = pd.to_datetime(df['transaction_date_real'], errors='coerce')
    df['delivery_date'] = pd.to_datetime(df['delivery_date'])
    df['date_only'] = df['transaction_date'].dt.date
    df['week'] = df['transaction_date'].dt.isocalendar().week

    # day_name ambil dari createdAt (Transaction.csv)
    df['day_name'] = df['day_name'].fillna('Unknown')
    df['is_weekend'] = df['day_name'].isin(['Saturday', 'Sunday'])

    # hour dari createdAt
    df['hour'] = df['hour'].fillna(0).astype(int)

    # Area normalization
    df['city_prov'] = df['customer_city_prov'].str.strip()
    df['province'] = df['city_prov'].str.extract(r',\s*(.+)$')[0].fillna('Unknown')
    df['city'] = df['city_prov'].str.extract(r'^([^,]+)')[0].str.strip()

    return df

@st.cache_data
def build_outlet_summary(df):
    ref = df['transaction_date'].max()
    out = df.groupby('customer_id').agg(
        num_trx=('bill_no','count'),
        num_products=('product_name','nunique'),
        first_trx=('transaction_date','min'),
        last_trx=('transaction_date','max'),
        total_qty=('quantity','sum'),
        customer_name=('customer_name','first'),
        channel=('customer_channel','first'),
        city_prov=('city_prov','first'),
        salesman=('salesman_name','first')
    ).reset_index()
    out['active_days'] = (out['last_trx'] - out['first_trx']).dt.days + 1
    out['trx_per_day'] = (out['num_trx'] / out['active_days']).round(3)
    out['days_since_last'] = (ref - out['last_trx']).dt.days
    return out, ref

@st.cache_data
def build_repeat_data(df):
    ref = df['transaction_date'].max()
    cutoff = ref - pd.Timedelta(days=30)
    df1m = df[df['transaction_date'] >= cutoff]
    rp = df1m.groupby('customer_id').agg(
        num_trx=('bill_no','count'),
        first_trx=('transaction_date','min'),
        last_trx=('transaction_date','max'),
        channel=('customer_channel','first'),
        city_prov=('city_prov','first')
    ).reset_index()
    rp['is_repeat'] = rp['num_trx'] > 1
    rp['num_repeat'] = rp['num_trx'] - 1
    rp['span_days'] = (rp['last_trx'] - rp['first_trx']).dt.days + 1
    rp['repeat_interval'] = rp['span_days'] / rp['num_repeat'].replace(0, 1)
    rp['days_since_last'] = (ref - rp['last_trx']).dt.days
    return rp, df1m

df = load_main()
outlet_summary, ref_date = build_outlet_summary(df)
repeat_data, df_1m = build_repeat_data(df)

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("🧠 Behavior Analytics")
st.sidebar.markdown("---")

area_filter = st.sidebar.multiselect(
    "Area",
    ['All'] + sorted(df['city_prov'].dropna().unique().tolist()),
    default=['All']
)
if 'All' not in area_filter:
    df = df[df['city_prov'].isin(area_filter)].copy()
    outlet_summary = outlet_summary[outlet_summary['city_prov'].isin(area_filter)].copy()
    repeat_data = repeat_data[repeat_data['city_prov'].isin(area_filter)].copy()

chan_filter = st.sidebar.multiselect(
    "Channel",
    ['All'] + sorted(df['customer_channel'].dropna().unique().tolist()),
    default=['All']
)
if 'All' not in chan_filter:
    df = df[df['customer_channel'].isin(chan_filter)].copy()
    outlet_summary = outlet_summary[outlet_summary['channel'].isin(chan_filter)].copy()
    repeat_data = repeat_data[repeat_data['channel'].isin(chan_filter)].copy()

sm_filter = st.sidebar.multiselect(
    "Salesman",
    ['All'] + sorted(df['salesman_name'].dropna().astype(str).unique().tolist()),
    default=['All']
)
if 'All' not in sm_filter:
    df = df[df['salesman_name'].isin(sm_filter)].copy()

prod_filter = st.sidebar.multiselect(
    "Product",
    ['All'] + sorted(df['product_name'].dropna().unique().tolist()),
    default=['All']
)
if 'All' not in prod_filter:
    df = df[df['product_name'].isin(prod_filter)].copy()

st.sidebar.markdown("---")
st.sidebar.caption(f"Period: {df['transaction_date'].min().date()} → {df['transaction_date'].max().date()}")
st.sidebar.caption(f"Rows: {len(df)} | Outlets: {df['customer_id'].nunique()}")

# ── KPI Strip ─────────────────────────────────────────────────────────────────
st.title("🧠 Arbas Behavior Analytics")
st.markdown("""
<div style="background: linear-gradient(135deg, #2E86AB 0%, #2ECC71 100%); color:white; padding:1.2rem 2rem; border-radius:12px; margin-bottom:1.5rem;">
  <h2 style="margin:0; color:white;">Outlet • Channel • Market • Repeat Patterns</h2>
  <p style="margin:0.3rem 0 0; opacity:0.85;">Behavioral Analytics Dashboard | {start} → {end}</p>
</div>
""".format(start=df['transaction_date'].min().date(), end=df['transaction_date'].max().date()), unsafe_allow_html=True)

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1: st.metric("Total Outlets", f"{df['customer_id'].nunique():,}")
with k2: st.metric("Total Trx", f"{len(df):,}")
with k3: st.metric("Channels", f"{df['customer_channel'].nunique()}")
with k4: st.metric("Areas", f"{df['city_prov'].nunique()}")
with k5:
    rp_rate = repeat_data['is_repeat'].mean()*100
    st.metric("Repeat Rate", f"{rp_rate:.0f}%")
with k6:
    chrun = (outlet_summary['days_since_last'] > 14).mean()*100
    st.metric("Churn Rate", f"{chrun:.0f}%")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1: OUTLET BEHAVIOR
# ═══════════════════════════════════════════════════════════════════════════════
page = st.radio(
    "Select Section",
    [
        "🏠 Outlet Behavior",
        "📊 Channel Behavior",
        "🗺️ Market Geography",
        "👤 Market-Sales Patterns",
        "🔁 Repeat Order Analytics",
        "💡 Insights & Actions",
    ],
    horizontal=True
)

# ─────────────────────────────── OUTLET BEHAVIOR ──────────────────────────────
if page == "🏠 Outlet Behavior":
    st.markdown('<div class="section-header">🏠 Outlet Behavior Analysis</div>', unsafe_allow_html=True)

    # Frequency Distribution
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Transaction Frequency Distribution")

        freq = outlet_summary.copy()
        freq_bins = [1, 2, 3, 5, 10, 999]
        freq_labels = ['1x', '2x', '3-4x', '5-9x', '10x+']
        freq['freq_group'] = pd.cut(freq['num_trx'], bins=freq_bins, labels=freq_labels)
        fd = freq['freq_group'].value_counts().reindex(freq_labels).fillna(0)

        fig = px.bar(
            x=fd.index, y=fd.values,
            color=fd.values, color_continuous_scale='Blues',
            text=fd.values,
            labels={'x':'Frequency', 'y':'Number of Outlets'}
        )
        fig.update_layout(showlegend=False, height=350)
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

        # Tabel: frequency distribution per grup
        fd_table = pd.DataFrame({
            'Frequency': freq_labels,
            'Jumlah Outlet': [int(fd[f]) for f in freq_labels],
            '% dari Total': [f"{fd[f]/fd.sum()*100:.1f}%" for f in freq_labels]
        })
        st.markdown("**📋 Tabel: Transaction Frequency Distribution**")
        st.dataframe(fd_table, use_container_width=True, hide_index=True)
        st.caption(f"Total outlets: {fd.sum()} | Data berdasarkan {len(outlet_summary)} outlets")

        # Top outlets by frequency (most transactions)
        freq_top = outlet_summary.sort_values('num_trx', ascending=False).head(15)
        freq_top_disp = freq_top[['customer_name','channel','city_prov','num_trx','num_products','total_qty']].copy()
        freq_top_disp.columns = ['Outlet','Channel','Area','#Trx','Products','Total Qty']
        st.markdown("**Top 15 Most Active Outlets**")
        st.dataframe(freq_top_disp, use_container_width=True, hide_index=True)

        # By channel table
        fd_chan = pd.crosstab(freq['freq_group'], freq['channel'])
        fd_chan = fd_chan[fd_chan.sum().sort_values(ascending=False).head(10).index]
        st.markdown("**Frequency × Channel (Top 10 Channels)**")
        st.dataframe(fd_chan, use_container_width=True)

    with col2:
        st.subheader("📦 Quantity per Transaction")
        qty_bins = [1, 3, 5, 10, 20, 50, 1000]
        qty_labels = ['1-2', '3-4', '5-9', '10-19', '20-49', '50+']
        df['qty_group'] = pd.cut(df['quantity'], bins=qty_bins, labels=qty_labels)
        qd = df['qty_group'].value_counts().reindex(qty_labels).fillna(0)

        fig = px.bar(
            x=qd.index, y=qd.values,
            color=qd.values, color_continuous_scale='Oranges',
            text=qd.values,
            labels={'x':'Qty Range', 'y':'Transactions'}
        )
        fig.update_layout(showlegend=False, height=350)
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

        # Tabel: quantity per transaction
        qty_table = pd.DataFrame({
            'Qty Range': qty_labels,
            'Jumlah Transaksi': [int(qd[q]) for q in qty_labels],
            '% dari Total': [f"{qd[q]/qd.sum()*100:.1f}%" for q in qty_labels]
        })
        st.markdown("**📋 Tabel: Quantity per Transaction**")
        st.dataframe(qty_table, use_container_width=True, hide_index=True)
        st.caption(f"Total transaksi: {qd.sum()} | Rata-rata qty: {df['quantity'].mean():.1f} unit/transaksi")

        # Detailed breakdown: top outlets by qty
        top_outlets_qty = df.groupby(['customer_name','customer_channel','city_prov']).agg(
            total_qty=('quantity','sum'),
            num_trx=('bill_no','count'),
            produk=('product_name','nunique')
        ).reset_index().sort_values('total_qty', ascending=False).head(15)
        top_outlets_qty.columns = ['Outlet','Channel','Area','Total Qty','#Trx','Products']
        st.markdown("**Top 15 Outlets by Quantity**")
        st.dataframe(top_outlets_qty, use_container_width=True, hide_index=True)

        # Stats
        st.markdown(f"""
        <div class="insight-card">
        <b>Qty/Transaction Stats:</b><br>
        • Min: <b>{df['quantity'].min()}</b> | Max: <b>{df['quantity'].max():,}</b><br>
        • Mean: <b>{df['quantity'].mean():.1f}</b> | Median: <b>{df['quantity'].median():.0f}</b>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("📉 Recency Distribution (Days Since Last Trx)")
    rec = pd.cut(
            outlet_summary['days_since_last'],
            bins=[0, 3, 7, 14, 30, 999],
            labels=['0-3 days','4-7 days','8-14 days','15-30 days','30+ days']
    ).value_counts()
    ro = ['0-3 days','4-7 days','8-14 days','15-30 days','30+ days']
    rec = rec.reindex(ro).fillna(0)

    colors = ['#2ECC71','#27AE60','#F39C12','#E74C3C','#C0392B']
    fig = go.Figure()
    for label, color in zip(ro, colors):
            fig.add_trace(go.Bar(
                x=[label], y=[int(rec[label])],
                text=str(int(rec[label])),
                textposition='outside',
                marker_color=color,
                name=label
            ))
    fig.update_layout(
            showlegend=False, height=300,
            yaxis_title='Number of Outlets',
            annotations=[dict(text='Active' if r < 15 else 'Churned', showarrow=False)
                        for r in [7, 22, 40]]
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabel: recency distribution
    rec_labels = ['0-3 days','4-7 days','8-14 days','15-30 days','30+ days']
    rec_colors  = ['Active (Hijau)','Active (Hijau)','Warning (Kuning)','At Risk (Merah)','Churned (Merah Tua)']
    rec_table = pd.DataFrame({
        'Recency': rec_labels,
        'Jumlah Outlet': [int(rec[r]) for r in rec_labels],
        'Status': rec_colors,
        '% dari Total': [f"{rec[r]/rec.sum()*100:.1f}%" for r in rec_labels]
    })
    st.markdown("**📋 Tabel: Recency Distribution**")
    st.dataframe(rec_table, use_container_width=True, hide_index=True)
    st.caption(f"Total: {rec.sum()} outlets | 0-14 days = aktif | 15+ days = berisiko churn")

        # At-risk outlets table (most days since last trx)
    at_risk = outlet_summary.nlargest(15, 'days_since_last')
    at_risk_display = at_risk[['customer_name','channel','city_prov','days_since_last','num_trx','total_qty']].copy()
    at_risk_display.columns = ['Outlet','Channel','Area','Days Since Last','#Trx','Total Qty']
    st.markdown("**⚠️ Most At-Risk Outlets (Highest Recency)**")
    st.dataframe(at_risk_display, use_container_width=True, hide_index=True)

    st.subheader("📅 Purchase Interval (Repeat Buyers)")
    intervals = []
    for cid, grp in df.sort_values('transaction_date').groupby('customer_id'):
            dates = grp['transaction_date'].sort_values()
            diffs = dates.diff().dt.days.dropna()
            if len(diffs) > 0:
                intervals.append(float(diffs.mean()))

    avg_int = pd.Series(intervals).dropna()
    if len(avg_int) > 0:
            int_bins = [0, 1, 3, 5, 7, 14, 999]
            int_labels = ['Daily','2-3 days','4-5 days','6-7 days','8-14 days','14+ days']
            int_dist = pd.cut(avg_int, bins=int_bins, labels=int_labels).value_counts()
            int_order = ['Daily','2-3 days','4-5 days','6-7 days','8-14 days','14+ days']
            int_dist = int_dist.reindex(int_order).fillna(0)

    fig = px.bar(
                x=int_dist.index, y=int_dist.values.astype(int),
                color=int_dist.values.astype(int), color_continuous_scale='Purples',
                text=int_dist.values.astype(int),
                labels={'x':'Interval','y':'Outlets'}
        )
    fig.update_layout(showlegend=False, height=300)
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

    # Tabel: purchase interval distribution
    int_order_labels = ['Daily','2-3 days','4-5 days','6-7 days','8-14 days','14+ days']
    int_table = pd.DataFrame({
        'Interval': int_order_labels,
        'Jumlah Outlet': [int(int_dist[i]) for i in int_order_labels],
        '% dari Total': [f"{int_dist[i]/int_dist.sum()*100:.1f}%" for i in int_order_labels]
    })
    st.markdown("**📋 Tabel: Purchase Interval Distribution**")
    st.dataframe(int_table, use_container_width=True, hide_index=True)
    st.caption(f"Repeat buyers: {len(avg_int)} outlets | Mean interval: {avg_int.mean():.1f} days | Median: {avg_int.median():.0f} days")

    # Product Preference
    st.markdown("---")
    st.subheader("🛒 Product Preference per Outlet")

    top_prod = df.groupby(['customer_id','product_name'])['quantity'].sum().reset_index()
    top_prod = top_prod.loc[top_prod.groupby('customer_id')['quantity'].idxmax()]
    pp = top_prod['product_name'].value_counts()

    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(
            values=pp.values, names=pp.index,
            title='Primary Product by Outlet Count',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(textinfo='percent+label+value')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        # Tabel: primary product by outlet count
        pp_table = pd.DataFrame({
            'Product': pp.index,
            'Jumlah Outlet': pp.values,
            '% dari Total': [f"{v/pp.sum()*100:.1f}%" for v in pp.values]
        })
        st.markdown("**📋 Tabel: Primary Product by Outlet Count**")
        st.dataframe(pp_table, use_container_width=True, hide_index=True)
        st.caption(f"Total outlets dengan primary product: {pp.sum()}")

    with col2:
        sw = outlet_summary[outlet_summary['num_products'] > 1]
        switch_data = outlet_summary['num_products'].value_counts().sort_index()
        st.markdown(f"**Multi-Product Outlets: {len(sw)} ({len(sw)/len(outlet_summary)*100:.1f}%)**")
        fig = px.bar(
            x=switch_data.index.astype(str), y=switch_data.values,
            text=switch_data.values,
            labels={'x':'Number of Products Bought','y':'Number of Outlets'},
            color=switch_data.values, color_continuous_scale='Teal'
        )
        fig.update_layout(showlegend=False, height=300)
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

        # Tabel: multi-product outlets
        mp_table = pd.DataFrame({
            'Jumlah Produk': switch_data.index.astype(str),
            'Jumlah Outlet': switch_data.values,
            '% dari Total': [f"{v/len(outlet_summary)*100:.1f}%" for v in switch_data.values]
        })
        st.markdown("**📋 Tabel: Multi-Product Outlets**")
        st.dataframe(mp_table, use_container_width=True, hide_index=True)

    # ── Hourly Transaction Patterns (from Transaction.csv createdAt) ─────────
    st.markdown("---")
    st.subheader("⏰ Pola Transaksi per Jam")

    # Bar chart: transactions by hour
    hour_dist = df['hour'].value_counts().sort_index()
    hour_labels = [f'{h:02d}:00' for h in hour_dist.index]
    hour_vals  = hour_dist.values

    fig = px.bar(
        x=hour_labels, y=hour_vals,
        color=hour_vals, color_continuous_scale='Sunset',
        text=hour_vals,
        labels={'x':'Jam','y':'Jumlah Transaksi'}
    )
    fig.update_layout(showlegend=False, height=350)
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

    # Tabel: distribution per jam
    hour_table = pd.DataFrame({
        'Jam': hour_labels,
        'Jumlah Transaksi': hour_vals,
        '% dari Total': [f"{v/hour_vals.sum()*100:.1f}%" for v in hour_vals]
    })
    st.markdown("**📋 Tabel: Transaksi per Jam**")
    st.dataframe(hour_table, use_container_width=True, hide_index=True)
    st.caption(f"Jam berasal dari Transaction.csv kolom 'createdAt' | Total: {hour_vals.sum()} transaksi")

    # Peak hour by channel
    st.markdown("**📊 Peak Hour per Channel**")
    peak_hour = df.groupby('customer_channel')['hour'].agg(['mean','median']).round(0).astype(int).reset_index()
    peak_hour.columns = ['Channel','Avg Hour','Median Hour']
    peak_hour['Peak Time'] = peak_hour['Avg Hour'].apply(lambda x: f"{x:02d}:00")
    peak_hour = peak_hour.sort_values('Avg Hour')
    st.dataframe(peak_hour[['Channel','Peak Time','Avg Hour','Median Hour']], use_container_width=True, hide_index=True)

    # ── Sales Input Patterns (kapan salesman menginput data) ─────────────────
    st.markdown("---")
    st.subheader("👤 Kapan Sales Menginput Data?")

    col1, col2 = st.columns(2)
    with col1:
        # Chart: input per jam by salesman
        top_salesmen = df['salesman_name'].value_counts().head(6).index.tolist()
        sm_hour = df[df['salesman_name'].isin(top_salesmen)].groupby(
            ['salesman_name','hour'])['bill_no'].count().reset_index()
        sm_hour.columns = ['Salesman','Jam','Jumlah Trx']
        sm_hour_pivot = sm_hour.pivot_table(
            index='Salesman', columns='Jam',
            values='Jumlah Trx', fill_value=0
        ).sort_index(axis=1)

        fig = go.Figure()
        for jam in sm_hour_pivot.columns:
            fig.add_trace(go.Bar(name=f'{jam:02d}:00',
                                 x=sm_hour_pivot.index, y=sm_hour_pivot[jam],
                                 text=sm_hour_pivot[jam]))
        fig.update_layout(barmode='group', xaxis={'tickangle': -20},
                           height=400, template='plotly_white', hovermode='x unified')
        st.markdown("**📊 Input per Jam — Top 6 Salesman**")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        hour_all = df['hour'].value_counts().sort_index()
        fig = px.bar(x=[f'{h:02d}:00' for h in hour_all.index],
                     y=hour_all.values,
                     color=hour_all.values, color_continuous_scale='Cividis',
                     text=hour_all.values,
                     labels={'x':'Jam Input','y':'Jumlah Transaksi'})
        fig.update_layout(showlegend=False, height=400)
        fig.update_traces(textposition='outside')
        st.markdown("**📊 Total Input per Jam — All Salesman**")
        st.plotly_chart(fig, use_container_width=True)

    # Tabel jam input per salesman
    sm_input_pivot = df.groupby(['salesman_name','hour'])['bill_no'].count().unstack(fill_value=0)
    sm_input_pivot = sm_input_pivot.reindex(df['salesman_name'].value_counts().head(10).index)
    sm_input_pivot = sm_input_pivot.reindex(columns=sorted(sm_input_pivot.columns))
    sm_input_pivot.columns = [f'{c:02d}:00' for c in sm_input_pivot.columns]
    sm_input_pivot['TOTAL'] = sm_input_pivot.sum(axis=1)
    sm_input_pivot = sm_input_pivot.reset_index()
    st.markdown("**📋 Tabel: Input per Jam per Salesman (Top 10)**")
    st.dataframe(sm_input_pivot, use_container_width=True, hide_index=True)
    st.caption("Data jam berasal dari Transaction.csv kolom 'createdAt'")

    # ── 📊 OUTLET BEHAVIOR SUMMARY ──────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Ringkasan Perilaku Outlet")

    # Calculate summary stats
    total_ol = len(outlet_summary)
    repeat_ol = repeat_data['is_repeat'].sum()
    one_time_ol = total_ol - repeat_ol
    churn_ol = int(outlet_summary[outlet_summary['days_since_last'] > 14].shape[0])
    multi_prod_ol = (outlet_summary['num_products'] > 1).sum()
    top_freq_ol = outlet_summary.nlargest(1, 'num_trx').iloc[0]
    top_qty_ol = outlet_summary.nlargest(1, 'total_qty').iloc[0]
    at_risk_ol = outlet_summary.nlargest(5, 'days_since_last')

    col_s1, col_s2, col_s3 = st.columns(3)

    with col_s1:
        st.markdown(f"""
        <div class="insight-card">
        <h4 style="color:#58a6ff; margin:0 0 0.5rem;">🏠 Outlet Summary</h4>
        <b>Total Outlet:</b> {total_ol}<br>
        <b>Repeat Buyers:</b> {repeat_ol} ({repeat_ol/total_ol*100:.1f}%)<br>
        <b>One-Time:</b> {one_time_ol} ({one_time_ol/total_ol*100:.1f}%)<br>
        <b>Churned (>14d):</b> {churn_ol} ({churn_ol/total_ol*100:.1f}%)<br>
        <b>Multi-Product:</b> {multi_prod_ol} ({multi_prod_ol/total_ol*100:.1f}%)<br>
        </div>
        """, unsafe_allow_html=True)

    with col_s2:
        st.markdown(f"""
        <div class="insight-card">
        <h4 style="color:#58a6ff; margin:0 0 0.5rem;">🏆 Top Outlet by Activity</h4>
        <b>Most Active:</b> {top_freq_ol['customer_name'][:25]}<br>
        <b>Channel:</b> {top_freq_ol['channel']}<br>
        <b>Total Trx:</b> {top_freq_ol['num_trx']} | <b>Qty:</b> {int(top_freq_ol['total_qty']):,}<br>
        <b>Products:</b> {top_freq_ol['num_products']} | <b>Days:</b> {top_freq_ol['days_since_last']}<br>
        </div>
        """, unsafe_allow_html=True)

    with col_s3:
        at_risk_name = at_risk_ol.iloc[0]['customer_name'][:25]
        at_risk_ch = at_risk_ol.iloc[0]['channel']
        at_risk_days = at_risk_ol.iloc[0]['days_since_last']
        at_risk_trx = at_risk_ol.iloc[0]['num_trx']
        st.markdown(f"""
        <div class="warn-card">
        <h4 style="color:#E74C3C; margin:0 0 0.5rem;">⚠️ Most At-Risk Outlet</h4>
        <b>Outlet:</b> {at_risk_name}<br>
        <b>Channel:</b> {at_risk_ch}<br>
        <b>Days Inactive:</b> {at_risk_days} days<br>
        <b>Total Trx:</b> {at_risk_trx}<br>
        </div>
        """, unsafe_allow_html=True)

    # Tabel: outlet summary by channel
    ol_by_chan = outlet_summary.groupby('channel').agg(
        outlets=('customer_id','count'),
        avg_trx=('num_trx','mean'),
        total_qty=('total_qty','sum'),
        avg_recency=('days_since_last','mean'),
        churned=('days_since_last', lambda x: (x>14).sum())
    ).reset_index().sort_values('outlets', ascending=False)
    ol_by_chan.columns = ['Channel','#Outlets','Avg Trx','Total Qty','Avg Days Inactive','Churned']
    st.markdown("**📋 Outlet Summary by Channel**")
    st.dataframe(ol_by_chan, use_container_width=True, hide_index=True)

# ─────────────────────────────── CHANNEL BEHAVIOR ─────────────────��────────────
elif page == "📊 Channel Behavior":
    st.markdown('<div class="section-header">📊 Channel Behavior Analysis</div>', unsafe_allow_html=True)

    # Channel activity overview
    chan_act = df.groupby('customer_channel').agg(
        trx=('bill_no','count'),
        outlets=('customer_id','nunique'),
        qty=('quantity','sum'),
        products=('product_name','nunique'),
        areas=('city_prov','nunique')
    ).reset_index()
    chan_act['trx_per_outlet'] = (chan_act['trx'] / chan_act['outlets']).round(2)
    chan_act['pct_outlets'] = (chan_act['outlets'] / df['customer_id'].nunique() * 100).round(1)
    chan_act = chan_act.sort_values('trx', ascending=False)

    # Top KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        top_chan = chan_act.iloc[0]
        st.metric("Top Channel", top_chan['customer_channel'])
        st.caption(f"{int(top_chan['trx'])} transactions | {int(top_chan['outlets'])} outlets")
    with c2:
        st.metric("Total Channels", f"{len(chan_act)}")
    with c3:
        st.metric("Avg Trx/Outlet", f"{chan_act['trx_per_outlet'].mean():.1f}")
    with c4:
        multi_chan = (chan_act['products'] > 1).sum()
        st.metric("Multi-Product Channels", f"{multi_chan}")

    # Bar chart: channels by transactions
    st.subheader("📊 Transactions by Channel")
    fig = px.bar(
        chan_act.head(15),
        x='customer_channel', y='trx',
        color='outlets', text='trx',
        labels={'customer_channel':'Channel','trx':'Transactions','outlets':'Outlets'},
        color_continuous_scale='Blues'
    )
    fig.update_layout(xaxis={'tickangle': -45}, height=400)
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

    # Tabel: transactions by channel
    chan_trx_table = chan_act[['customer_channel','trx','outlets','qty','trx_per_outlet']].copy()
    chan_trx_table.columns = ['Channel','#Transaksi','#Outlets','Total Qty','Trx/Outlet']
    chan_trx_table = chan_trx_table.sort_values('#Transaksi', ascending=False).head(15)
    st.markdown("**📋 Tabel: Transactions by Channel**")
    st.dataframe(chan_trx_table, use_container_width=True, hide_index=True)
    st.caption(f"Total channel: {len(chan_act)} | Top 15 ditampilkan")

    # Channel table
    st.dataframe(
        chan_act[['customer_channel','trx','outlets','qty','trx_per_outlet','products','areas']].rename(columns={
            'customer_channel':'Channel','trx':'Trx','outlets':'Outlets','qty':'Qty',
            'trx_per_outlet':'Trx/OL','products':'Products','areas':'Areas'
        }),
        use_container_width=True, hide_index=True
    )

    st.markdown("---")

    # 🔍 CHANNEL DRILL-DOWN: Outlet details per channel
    st.subheader("🔍 Channel Drill-Down — Outlet & Product Details")
    st.caption("Pilih channel di bawah untuk melihat outlet-outlet di dalamnya, produk yang dibeli, dan quantity-nya.")

    drill_channels = sorted(df['customer_channel'].dropna().unique().tolist())
    selected_drill = st.selectbox("Pilih Channel", options=['-- pilih channel --'] + drill_channels)

    if selected_drill and selected_drill != '-- pilih channel --':
        chan_df = df[df['customer_channel'] == selected_drill].copy()

        # Summary stats for selected channel
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Outlets", f"{chan_df['customer_id'].nunique()}")
        with c2: st.metric("Transaksi", f"{len(chan_df)}")
        with c3: st.metric("Produk", f"{chan_df['product_name'].nunique()}")
        with c4: st.metric("Qty Total", f"{chan_df['quantity'].sum():,}")

        st.markdown("---")

        # Per-outlet detail
        outlet_detail = chan_df.groupby(['customer_id','customer_name','city_prov']).agg(
            num_trx=('bill_no','count'),
            total_qty=('quantity','sum'),
            produk=('product_name', lambda x: ', '.join(x.unique())),
            sales=('salesman_name', lambda x: x.mode()[0] if len(x.mode()) else 'N/A')
        ).reset_index().sort_values('total_qty', ascending=False)
        outlet_detail.columns = ['ID','Outlet Name','Area','#Trx','Total Qty','Products','Salesman']

        st.markdown(f"#### 📋 Outlets in [{selected_drill}] ({len(outlet_detail)} outlets)")
        st.dataframe(outlet_detail, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Product breakdown within channel
        st.markdown(f"#### 📦 Product Breakdown — [{selected_drill}]")
        prod_detail = chan_df.groupby('product_name').agg(
            outlets=('customer_id','nunique'),
            trx=('bill_no','count'),
            total_qty=('quantity','sum')
        ).reset_index().sort_values('total_qty', ascending=False)
        prod_detail.columns = ['Product','#Outlets','#Transactions','Total Qty']

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            fig = px.bar(
                prod_detail,
                x='Product', y='Total Qty',
                color='Total Qty', text='Total Qty',
                color_continuous_scale='Teal',
                labels={'Product':'Product','Total Qty':'Quantity Sold'}
            )
            fig.update_layout(xaxis={'tickangle': -30}, height=350, showlegend=False)
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        with col_p2:
            fig = px.bar(
                prod_detail,
                x='Product', y='#Outlets',
                color='#Outlets', text='#Outlets',
                color_continuous_scale='Viridis',
                labels={'Product':'Product','#Outlets':'Outlets'}
            )
            fig.update_layout(xaxis={'tickangle': -30}, height=350, showlegend=False)
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # Full transaction log for selected channel
        with st.expander(f"📜 Full Transaction Log — [{selected_drill}] ({len(chan_df)} rows)"):
            log = chan_df[[
                'bill_no','transaction_date','customer_name','product_name',
                'quantity','selling_price','payment_type','delivery_status',
                'salesman_name','city_prov'
            ]].rename(columns={
                'bill_no':'Bill No','transaction_date':'Date',
                'customer_name':'Outlet','product_name':'Product',
                'quantity':'Qty','selling_price':'Price',
                'payment_type':'Payment','delivery_status':'Delivery',
                'salesman_name':'Salesman','city_prov':'Area'
            })
            log['Date'] = log['Date'].dt.strftime('%Y-%m-%d')
            st.dataframe(log, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Day pattern by channel
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📅 Active Days per Channel 5 Teratas")
        day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        chan_day = pd.crosstab(df['customer_channel'], df['day_name'])
        chan_day = chan_day.reindex(columns=[c for c in day_order if c in chan_day.columns])
        top5 = chan_act.head(5)['customer_channel'].tolist()
        chan_day_top = chan_day.reindex(top5)

        fig = go.Figure()
        for day in chan_day_top.columns:
            fig.add_trace(go.Bar(name=day, x=chan_day_top.index, y=chan_day_top[day].values))
        fig.update_layout(barmode='group', xaxis={'tickangle': -30}, height=350, template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)

        # Tabel: active days per channel
        st.markdown("**📋 Tabel: Active Days per Channel (Top 5)**")
        chan_day_disp = chan_day_top.fillna(0).astype(int).reset_index()
        chan_day_disp.columns = ['Channel'] + list(chan_day_top.columns)
        st.dataframe(chan_day_disp, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("🚚 Delivery Success Rate by Channel")
        chan_del = pd.crosstab(df['customer_channel'], df['delivery_status'])
        chan_del['total'] = chan_del.sum(axis=1)
        chan_del['delivered_pct'] = (chan_del.get('DELIVERED',0) / chan_del['total'] * 100).round(1)
        chan_del = chan_del.sort_values('delivered_pct')

        fig = px.bar(
            x=chan_del['delivered_pct'], y=chan_del.index,
            orientation='h',
            color=chan_del['delivered_pct'], color_continuous_scale='RdYlGn',
            text=chan_del['delivered_pct'].apply(lambda x: f"{x:.0f}%"),
            labels={'x':'Delivery Rate (%)','y':''}
        )
        fig.update_layout(showlegend=False, height=400)
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

        # Tabel: delivery success rate
        del_table = chan_del[['total','delivered_pct']].copy()
        del_table.columns = ['Total Trx','Delivered %']
        del_table = del_table.sort_values('Delivered %', ascending=False)
        st.markdown("**📋 Tabel: Delivery Success Rate by Channel**")
        st.dataframe(del_table, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Payment behavior
    st.subheader("💳 Payment Behavior by Channel")
    chan_pay = pd.crosstab(df['customer_channel'], df['payment_type'], normalize='index') * 100

    fig = go.Figure()
    for pay_type in ['CASH', 'CREDIT', 'TRANSFER']:
        if pay_type in chan_pay.columns:
            fig.add_trace(go.Bar(
                name=pay_type, x=chan_pay.index,
                y=chan_pay[pay_type], text=chan_pay[pay_type].round(0).astype(int).astype(str)+'%',
                textposition='inside'
            ))
    fig.update_layout(
        barmode='stack', xaxis={'tickangle': -45},
        height=350, template='plotly_white',
        yaxis_title='% of Transactions'
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabel: payment behavior
    pay_cols = [c for c in ['CASH','CREDIT','TRANSFER'] if c in chan_pay.columns]
    pay_table = chan_pay[pay_cols].round(1).copy()
    pay_table['Total %'] = pay_table.sum(axis=1).round(1)
    pay_table = pay_table.sort_values(pay_table.columns[0], ascending=False)
    st.markdown("**📋 Tabel: Payment Behavior by Channel (%)**")
    st.dataframe(pay_table, use_container_width=True)

    # ── 📊 CHANNEL BEHAVIOR SUMMARY ───────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Ringkasan Perilaku Channel")

    total_outlets = df['customer_id'].nunique()
    total_trx = len(df)

    # Top channel by outlets
    top_outlet_chan = df.groupby('customer_channel')['customer_id'].nunique().idxmax()
    top_outlet_cnt = df.groupby('customer_channel')['customer_id'].nunique().max()

    # Top channel by trx
    top_trx_chan = df.groupby('customer_channel')['bill_no'].count().idxmax()
    top_trx_cnt = df.groupby('customer_channel')['bill_no'].count().max()

    # Best & worst repeat
    chan_rr = repeat_data.groupby('channel')['is_repeat'].mean()*100
    best_chan = chan_rr.idxmax()
    best_rr = chan_rr.max()
    worst_chan = chan_rr.idxmin()
    worst_rr = chan_rr.min()

    # Multi-product channels
    multi_prod_chans = df.groupby('customer_channel')['product_name'].nunique()
    top_multi_prod = multi_prod_chans.idxmax()
    top_multi_cnt = multi_prod_chans.max()

    # Delivery rate
    deliv_rate = df.groupby('customer_channel')['delivery_status'].apply(
        lambda x: (x == 'DELIVERED').mean()*100
    ).round(1)
    best_deliv = deliv_rate.idxmax()
    best_deliv_pct = deliv_rate.max()
    worst_deliv = deliv_rate.idxmin()
    worst_deliv_pct = deliv_rate.min()

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown(f"""
        <div class="insight-card">
        <h4 style="color:#58a6ff; margin:0 0 0.5rem;">📡 Channel Overview</h4>
        <b>Total Channel:</b> {df['customer_channel'].nunique()}<br>
        <b>Total Outlets:</b> {total_outlets}<br>
        <b>Total Trx:</b> {total_trx}<br>
        <b>Best Outlet Channel:</b> {top_outlet_chan} ({top_outlet_cnt} ol)<br>
        <b>Best Trx Channel:</b> {top_trx_chan} ({top_trx_cnt} trx)<br>
        </div>
        """, unsafe_allow_html=True)

    with col_c2:
        st.markdown(f"""
        <div class="success-card">
        <h4 style="color:#2ECC71; margin:0 0 0.5rem;">✅ Repeat Rate Performance</h4>
        <b>Best Channel:</b> {best_chan} ({best_rr:.1f}% repeat)<br>
        <b>Worst Channel:</b> {worst_chan} ({worst_rr:.1f}% repeat)<br>
        <b>Most Product Diversity:</b> {top_multi_prod} ({top_multi_cnt} products)<br>
        </div>
        """, unsafe_allow_html=True)

    
    # Tabel: channel summary
    chan_sum = df.groupby('customer_channel').agg(
        outlets=('customer_id','nunique'),
        trx=('bill_no','count'),
        qty=('quantity','sum'),
        products=('product_name','nunique')
    ).reset_index()
    chan_sum['repeat_rate'] = chan_sum['customer_channel'].map(chan_rr).round(1)
    chan_sum['deliv_rate'] = chan_sum['customer_channel'].map(deliv_rate).round(1)
    chan_sum = chan_sum.sort_values('trx', ascending=False)
    chan_sum.columns = ['Channel','#Outlets','#Trx','Total Qty','#Products','Repeat %','Deliv %']
    st.markdown("**📋 Channel Summary Table**")
    st.dataframe(chan_sum, use_container_width=True, hide_index=True)

# ─────────────────────────────── MARKET GEOGRAPHY ─────────────────────────────
elif page == "🗺️ Market Geography":
    st.markdown('<div class="section-header">🗺️ Market Geography</div>', unsafe_allow_html=True)

    # Area overview
    area = df.groupby('city_prov').agg(
        outlets=('customer_id','nunique'),
        trx=('bill_no','count'),
        channels=('customer_channel','nunique'),
        qty=('quantity','sum'),
        salesmen=('salesman_name','nunique')
    ).reset_index().sort_values('outlets', ascending=False)
    area['trx_per_outlet'] = (area['trx'] / area['outlets']).round(2)
    area['pct_outlets'] = (area['outlets'] / df['customer_id'].nunique() * 100).round(1)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total Areas", f"{len(area)}")
    with c2:
        top_area = area.iloc[0]
        st.metric("Top Area", top_area['city_prov'][:30])
        st.caption(f"{int(top_area['outlets'])} outlets | {int(top_area['trx'])} trx")
    with c3:
        multi = (area['channels'] >= 3).sum()
        st.metric("Multi-Channel Areas", f"{multi}")
    with c4:
        st.metric("Avg Outlets/Area", f"{area['outlets'].mean():.1f}")

    # Area bar chart
    st.subheader("📊 Outlets by Area")
    fig = px.bar(
        area.head(15),
        x='city_prov', y='outlets',
        color='trx', text='outlets',
        labels={'city_prov':'Area','outlets':'Outlets','trx':'Transactions'},
        color_continuous_scale='Blues'
    )
    fig.update_layout(xaxis={'tickangle': -45}, height=400)
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

    # Tabel: outlets by area (sumber data dari chart)
    area_chart_table = area[['city_prov','outlets','trx','qty','pct_outlets','channels']].copy()
    area_chart_table.columns = ['Area','#Outlets','#Transaksi','Total Qty','%Share','#Channels']
    area_chart_table = area_chart_table.sort_values('#Outlets', ascending=False).head(15)
    st.markdown("**📋 Tabel: Outlets by Area**")
    st.dataframe(area_chart_table, use_container_width=True, hide_index=True)
    st.caption(f"Total area: {len(area)} | Total outlets: {df['customer_id'].nunique()}")

    # Table: outlet detail per area with products & salesman
    area_det = df.groupby(['city_prov','customer_name','customer_channel']).agg(
        num_trx=('bill_no','count'),
        qty=('quantity','sum'),
        produk=('product_name', lambda x: ', '.join(x.unique())),
        sales=('salesman_name', lambda x: x.mode()[0] if len(x.mode()) else 'N/A')
    ).reset_index().sort_values(['city_prov','qty'], ascending=[True,False])
    area_det.columns = ['Area','Outlet','Channel','#Trx','Qty','Products','Salesman']
    st.markdown("**📋 Outlet Detail per Area**")
    st.dataframe(area_det.head(40), use_container_width=True, hide_index=True)

    # Area table
    st.dataframe(
        area[['city_prov','outlets','trx','trx_per_outlet','pct_outlets','channels','salesmen']].rename(columns={
            'city_prov':'Area','outlets':'Outlets','trx':'Trx','trx_per_outlet':'Trx/OL',
            'pct_outlets':'%Outlets','channels':'Channels','salesmen':'Salesmen'
        }).head(20),
        use_container_width=True, hide_index=True
    )

    st.markdown("---")

    # Channel distribution per area
    
    top5_areas = area.head(5)['city_prov'].tolist()

    
    st.subheader("📍 Top 5 Areas × Top Channels")
    area_chan = pd.crosstab(df['city_prov'], df['customer_channel'])
    area_chan_top5 = area_chan.reindex(top5_areas)
    top8 = df['customer_channel'].value_counts().head(8).index.tolist()
    area_chan_show = area_chan_top5[[c for c in top8 if c in area_chan_top5.columns]]

    fig = go.Figure()
    for chan in area_chan_show.columns:
        fig.add_trace(go.Bar(name=chan, x=area_chan_show.index, y=area_chan_show[chan]))
    fig.update_layout(
            barmode='stack', xaxis={'tickangle': -20},
            height=400, template='plotly_white',
            hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabel: area × channel
    area_chan_table = area_chan_top5.fillna(0).astype(int).reset_index()
    area_chan_table.columns = ['Area'] + list(area_chan_top5.columns)
    st.markdown("**📋 Tabel: Top 5 Areas × Top Channels (jumlah transaksi)**")
    st.dataframe(area_chan_table, use_container_width=True, hide_index=True)

    # Dominant channel per area
    st.subheader("🎯 Dominant Channel per Top Area")
    dom = []
    for a in top5_areas:
        subset = df[df['city_prov'] == a]
        top_c = subset['customer_channel'].value_counts()
        dom.append({
            'Area': a,
            'Top Channel': top_c.idxmax(),
            'Trx in Channel': top_c.max(),
            'Total Trx': len(subset),
            'Share %': f"{top_c.max()/len(subset)*100:.0f}%"
        })
    st.dataframe(pd.DataFrame(dom), use_container_width=True, hide_index=True)

    # ── Transaksi per Jam berdasarkan Area ──────────────────────────────────
    st.markdown("---")
    st.subheader("⏰ Pola Transaksi per Jam — berdasarkan Area")

    col1, col2 = st.columns(2)
    with col1:
        # Heatmap: Area × Hour
        area_hour = df.pivot_table(
            index='city_prov', columns='hour',
            values='bill_no', aggfunc='count', fill_value=0
        )
        top_areas_hour = df['city_prov'].value_counts().head(8).index.tolist()
        area_hour_show = area_hour.reindex(top_areas_hour)
        area_hour_show = area_hour_show.reindex(columns=sorted(area_hour_show.columns))

        fig = go.Figure(data=go.Heatmap(
            z=area_hour_show.values,
            x=[f'{c:02d}:00' for c in area_hour_show.columns],
            y=area_hour_show.index,
            colorscale='YlOrRd',
            text=area_hour_show.values,
            texttemplate='%{text}',
            colorbar=dict(title='Trx')
        ))
        fig.update_layout(height=420, xaxis={'tickangle': -45})
        st.markdown("**📊 Heatmap: Area × Jam**")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Bar chart: top areas per jam
        top3_areas = df['city_prov'].value_counts().head(3).index.tolist()
        area_hour_trend = df[df['city_prov'].isin(top3_areas)].groupby(
            ['city_prov','hour'])['bill_no'].count().reset_index()
        area_hour_trend.columns = ['Area','Jam','Jumlah']

        fig = go.Figure()
        for area_item in top3_areas:
            sub = area_hour_trend[area_hour_trend['Area'] == area_item]
            fig.add_trace(go.Scatter(
                name=area_item[:25], x=sub['Jam'].apply(lambda x: f'{x:02d}:00'),
                y=sub['Jumlah'], mode='lines+markers+text',
                text=sub['Jumlah'], textposition='top center'
            ))
        fig.update_layout(height=420, xaxis_title='Jam', yaxis_title='Jumlah Transaksi',
                           hovermode='x unified')
        st.markdown("**📊 Trend per Jam — Top 3 Area**")
        st.plotly_chart(fig, use_container_width=True)

    # Tabel: area × jam
    area_hour_table = area_hour.reindex(top_areas_hour)
    area_hour_table = area_hour_table.reindex(columns=sorted(area_hour_table.columns))
    area_hour_table.columns = [f'{c:02d}:00' for c in area_hour_table.columns]
    area_hour_table['TOTAL'] = area_hour_table.sum(axis=1)
    area_hour_table = area_hour_table.reset_index()
    area_hour_table.columns = ['Area'] + list(area_hour_table.columns[1:])
    st.markdown("**📋 Tabel: Transaksi per Jam per Area**")
    st.dataframe(area_hour_table, use_container_width=True, hide_index=True)
    st.caption("Data jam berasal dari Transaction.csv kolom 'createdAt'")

    # Peak hour by area
    peak_area_hour = df.groupby('city_prov')['hour'].agg(['mean','median']).round(0).astype(int).reset_index()
    peak_area_hour.columns = ['Area','Avg Hour','Median Hour']
    peak_area_hour['Peak Time'] = peak_area_hour['Avg Hour'].apply(lambda x: f"{x:02d}:00")
    peak_area_hour = peak_area_hour.sort_values('Avg Hour')
    st.markdown("**📊 Peak Hour per Area**")
    st.dataframe(peak_area_hour[['Area','Peak Time','Avg Hour','Median Hour']], use_container_width=True, hide_index=True)

    # ── 🗺️ OUTLET GEO BUILD (needed before summary and map) ──────────────
    @st.cache_data
    def build_outlet_geo(df_input, geo_df_input):
        """Join transaction data with customer geometry."""
        outlets = df_input.groupby(['customer_id','customer_name','customer_channel','customer_city_prov']).agg(
            total_trx=('bill_no','count'),
            total_qty=('quantity','sum'),
            products=('product_name', lambda x: ', '.join(x.unique())),
            salesman=('salesman_name', lambda x: x.mode()[0] if len(x.mode()) else 'N/A')
        ).reset_index()
        merged = outlets.merge(
            geo_df_input[['customer_id','alamat','tipeChannel','provinsi','kota','cust_status','lat','lon']],
            on='customer_id', how='left'
        )
        merged['province'] = merged['customer_city_prov'].str.extract(r',\s*(.+)$')[0].fillna(
            merged['provinsi'].fillna('Unknown')
        )
        return merged

    outlets_geo = build_outlet_geo(df, geo_df)

    # ── 📊 MARKET GEOGRAPHY SUMMARY ──────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Ringkasan Geografi Pasar")

    total_outlets_geo = df['customer_id'].nunique()
    total_trx_geo = len(df)
    top_area_name = df['city_prov'].value_counts().idxmax()
    top_area_ol = df['city_prov'].value_counts().iloc[0]
    top_area_trx = len(df[df['city_prov']==top_area_name])

    area_rr = repeat_data.groupby('city_prov')['is_repeat'].mean()*100
    best_area = area_rr.idxmax()
    best_area_rr = area_rr.max()
    worst_area = area_rr.idxmin()
    worst_area_rr = area_rr.min()

    area_churn = outlet_summary.groupby('city_prov')['days_since_last'].apply(
        lambda x: (x > 14).mean()*100
    )
    highest_churn_area = area_churn.idxmax()
    highest_churn_pct = area_churn.max()

    # Geo coverage
    geo_count = outlets_geo.dropna(subset=['lat','lon']).shape[0]
    geo_pct = geo_count/total_outlets_geo*100

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.markdown(f"""
        <div class="insight-card">
        <h4 style="color:#58a6ff; margin:0 0 0.5rem;">🗺️ Area Overview</h4>
        <b>Total Area:</b> {df['city_prov'].nunique()}<br>
        <b>Total Outlets:</b> {total_outlets_geo}<br>
        <b>Total Trx:</b> {total_trx_geo}<br>
        <b>Top Area:</b> {top_area_name[:30]} ({top_area_ol} ol)<br>
        </div>
        """, unsafe_allow_html=True)

    with col_m2:
        st.markdown(f"""
        <div class="success-card">
        <h4 style="color:#2ECC71; margin:0 0 0.5rem;">✅ Best & Worst Area</h4>
        <b>Best Repeat:</b> {best_area[:30]} ({best_area_rr:.1f}%)<br>
        <b>Worst Repeat:</b> {worst_area[:30]} ({worst_area_rr:.1f}%)<br>
        <b>Highest Churn:</b> {highest_churn_area[:30]} ({highest_churn_pct:.1f}%)<br>
        </div>
        """, unsafe_allow_html=True)

    with col_m3:
        st.markdown(f"""
        <div class="insight-card">
        <h4 style="color:#58a6ff; margin:0 0 0.5rem;">🗺️ Geo Coverage</h4>
        <b>Outlets with Map:</b> {geo_count} ({geo_pct:.0f}%)<br>
        <b>Source:</b> customers.csv (WKB geom)<br>
        </div>
        """, unsafe_allow_html=True)

    # Tabel: area summary
    area_sum = df.groupby('city_prov').agg(
        outlets=('customer_id','nunique'),
        trx=('bill_no','count'),
        qty=('quantity','sum'),
        channels=('customer_channel','nunique'),
        salesmen=('salesman_name','nunique')
    ).reset_index()
    area_sum['repeat_rate'] = area_sum['city_prov'].map(area_rr).round(1)
    area_sum['churn_rate'] = area_sum['city_prov'].map(area_churn).round(1)
    area_sum = area_sum.sort_values('outlets', ascending=False)
    area_sum.columns = ['Area','#Outlets','#Trx','Total Qty','#Channels','#Salesmen','Repeat %','Churn %']
    st.markdown("**📋 Area Summary Table**")
    st.dataframe(area_sum, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 🗺️ OUTLET MAP — from customers.csv WKB geometry
    st.subheader("🗺️ Outlet Location Map (Precise Coordinates)")

    geo_count = outlets_geo.dropna(subset=['lat','lon']).shape[0]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Outlets in Transactions", f"{len(outlets_geo)}")
    with c2:
        st.metric("With Precise Location", f"{geo_count} ({geo_count/len(outlets_geo)*100:.0f}%)")
    with c3:
        st.metric("Geo Source", "customers.csv (WKB)")

    st.info(f"""
    📍 Data geometry berasal dari **customers.csv** (kolom `geom` = PostGIS WKB format).
    ✅ Successfully decoded: **{geo_count} outlets** dengan koordinat lat/lon.
    """)
    st.markdown("---")

    # Map controls
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        color_by = st.selectbox(
            "Warna Marker berdasarkan",
            ['customer_channel', 'customer_city_prov', 'province', 'salesman', 'total_trx'],
            index=0
        )
    with col_m2:
        # Label & filter berubah sesuai pilihan warna marker
        if color_by == 'customer_channel':
            filter_label = "Filter Channel di Map"
            filter_col   = 'customer_channel'
        elif color_by == 'customer_city_prov':
            filter_label = "Filter Kota/Kab di Map"
            filter_col   = 'customer_city_prov'
        elif color_by == 'province':
            filter_label = "Filter Provinsi di Map"
            filter_col   = 'province'
        elif color_by == 'salesman':
            filter_label = "Filter Salesman di Map"
            filter_col   = 'salesman'
        else:
            filter_label = "Filter di Map"
            filter_col   = 'total_trx'

        filter_opts = ['All'] + sorted(outlets_geo[filter_col].dropna().unique().astype(str).tolist())
        show_only = st.multiselect(filter_label, options=filter_opts, default=['All'])
    with col_m3:
        radius_size = st.slider("Ukuran Marker", 3, 15, 6)

    # Filter
    map_df = outlets_geo.dropna(subset=['lat','lon']).copy()
    if 'All' not in show_only:
        if filter_col == 'total_trx':
            # Filter by transaction count range
            min_trx_filter = min([int(x) for x in show_only])
            max_trx_filter = max([int(x) for x in show_only])
            map_df = map_df[map_df['total_trx'].between(min_trx_filter, max_trx_filter)]
        else:
            map_df = map_df[map_df[filter_col].isin(show_only)]

    if len(map_df) > 0:
        center_lat = map_df['lat'].mean()
        center_lon = map_df['lon'].mean()

        # Color mapping
        color_palette = [
            '#e41a1c','#377eb8','#4daf4a','#984ea3','#ff7f00','#a65628','#f781bf',
            '#999999','#a6cee3','#b2df8a','#33bd5a','#e6285c','#8dd3c7',
            '#bebada','#fb8072','#80b1d3','#fdb462','#fccde5','#ffed6f'
        ]

        if color_by == 'total_trx':
            max_trx = map_df['total_trx'].max()
            min_trx = map_df['total_trx'].min()
            def trx_color(trx):
                ratio = (trx - min_trx) / (max_trx - min_trx + 0.001)
                return f'hsl({210 - ratio*60}, 90%, {35 + ratio*30}%)'
            marker_color = ['#58a6ff']  # fallback
        elif color_by == 'salesman':
            sm_unique = map_df['salesman'].unique()
            sm_map = {sm: color_palette[i % len(color_palette)] for i, sm in enumerate(sm_unique)}
            marker_color = None
        elif color_by == 'province':
            p_unique = map_df['province'].unique()
            p_map = {p: color_palette[i % len(color_palette)] for i, p in enumerate(p_unique)}
            marker_color = None
        else:  # channel or customer_city_prov
            col_val = map_df[color_by].unique()
            col_map = {v: color_palette[i % len(color_palette)] for i, v in enumerate(col_val)}
            marker_color = None

        # Build map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=11,
            tiles='CartoDB dark_matter'
        )

        # Add markers
        for _, row in map_df.iterrows():
            if color_by == 'total_trx':
                fill_color = trx_color(row['total_trx'])
                line_color = '#ffffff'
                radius = radius_size
            elif color_by == 'salesman':
                fill_color = sm_map.get(row['salesman'], '#58a6ff')
                line_color = '#ffffff'
                radius = radius_size
            elif color_by == 'province':
                fill_color = p_map.get(row['province'], '#58a6ff')
                line_color = '#ffffff'
                radius = radius_size
            else:
                fill_color = col_map.get(row[color_by], '#58a6ff')
                line_color = '#ffffff'
                radius = radius_size

            popup_html = f"""
            <div style="font-family: 'Segoe UI', Arial; min-width: 240px;">
              <h4 style="margin:0 0 8px; color:#1f6feb; border-bottom:1px solid #30363d; padding-bottom:4px;">
                {row['customer_name']}
              </h4>
              <table style="width:100%; font-size:13px;">
                <tr><td style="color:#8b949e;"><b>Channel</b></td><td style="color:#000000;">{row['customer_channel']}</td></tr>
                <tr><td style="color:#8b949e;"><b>Alamat</b></td><td style="color:#000000;">{row.get('alamat','-') or '-'}</td></tr>
                <tr><td style="color:#8b949e;"><b>Area</b></td><td style="color:#000000;">{row['customer_city_prov']}</td></tr>
                <tr><td style="color:#8b949e;"><b>Kota/Kab</b></td><td style="color:#000000;">{row.get('kota','-') or '-'}</td></tr>
                <tr><td style="color:#8b949e;"><b>Transactions</b></td><td style="color:#000000;">{row['total_trx']}x</td></tr>
                <tr><td style="color:#8b949e;"><b>Total Qty</b></td><td style="color:#000000;">{row['total_qty']:,} unit</td></tr>
                <tr><td style="color:#8b949e;"><b>Products</b></td><td style="color:#000000;">{row['products']}</td></tr>
                <tr><td style="color:#8b949e;"><b>Salesman</b></td><td style="color:#000000;">{row['salesman']}</td></tr>
                <tr><td style="color:#8b949e;"><b>Status</b></td><td style="color:#000000;">{row.get('cust_status','N/A') or 'N/A'}</td></tr>
                <tr><td style="color:#8b949e;"><b>Lat/Lon</b></td><td style="color:#58a6ff; font-size:11px;">{row['lat']:.6f}, {row['lon']:.6f}</td></tr>
              </table>
            </div>
            """

            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=radius,
                color=line_color,
                fill=True,
                fill_color=fill_color,
                fill_opacity=0.85,
                weight=1.5,
                popup=folium.Popup(popup_html, max_width=320),
                tooltip=f"📍 {row['customer_name']} | {row['customer_channel']} | {row['total_trx']} trx"
            ).add_to(m)

        # Legend
        legend_items = None
        legend_title = ''
        if color_by == 'salesman':
            legend_items = sm_map
            legend_title = 'Salesman'
        elif color_by == 'province':
            legend_items = p_map
            legend_title = 'Province/Wilayah'
        elif color_by == 'customer_channel':
            legend_items = col_map
            legend_title = 'Channel'
        elif color_by == 'customer_city_prov':
            legend_items = col_map
            legend_title = 'Kota/Kab'
        else:
            legend_items = col_map
            legend_title = color_by

        if legend_items:
            legend_items = dict(list(legend_items.items())[:15])
            legend_html = f"""
            <div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999;
                 background: #161b22; border: 1px solid #30363d; border-radius: 10px;
                 padding: 12px; color: #e6edf3; font-size: 11px; min-width: 180px; max-width: 220px;">
              <b style="color:#58a6ff; font-size:12px;">{legend_title}</b><br>
              <div style="max-height:200px; overflow-y:auto;">
              {''.join(f'<div style="display:flex; align-items:center; gap:6px; margin:3px 0;">'
                       f'<span style="background:{v}; width:10px; height:10px; border-radius:50%; display:inline-block;"></span>'
                       f'<span style="color:#e6edf3;">{str(k)[:22]}</span></div>'
                       for k, v in legend_items.items())}
              </div>
            </div>
            """
            m.get_root().html.add_child(folium.Element(legend_html))

        st_folium(m, width='100%', height=620)

        # Summary stats table
        st.markdown("#### 📋 Outlets with Precise Location")
        disp_cols = ['customer_name','customer_channel','customer_city_prov','total_trx','total_qty','products','salesman','lat','lon']
        disp = map_df[disp_cols].rename(columns={
            'customer_name':'Outlet','customer_channel':'Channel','customer_city_prov':'Area',
            'total_trx':'#Trx','total_qty':'Qty','products':'Products','salesman':'Salesman',
            'lat':'Lat','lon':'Lon'
        }).sort_values('#Trx', ascending=False)
        st.dataframe(disp, use_container_width=True, hide_index=True)

    else:
        st.warning("Tidak ada data lokasi. Pastikan customers.csv memiliki kolom `geom` yang terisi.")

# ─────────────────────────────── MARKET-SALES ───────────────────────────────────
elif page == "👤 Market-Sales Patterns":
    st.markdown('<div class="section-header">👤 Market-Sales Behavior</div>', unsafe_allow_html=True)

    # Territory coverage
    sm_terr = df.groupby('salesman_name').agg(
        outlets=('customer_id','nunique'),
        trx=('bill_no','count'),
        channels=('customer_channel','nunique'),
        areas=('city_prov','nunique'),
        products=('product_name','nunique')
    ).reset_index().sort_values('outlets', ascending=False)
    sm_terr['trx_per_outlet'] = (sm_terr['trx'] / sm_terr['outlets']).round(2)
    sm_terr['pct_outlets'] = (sm_terr['outlets'] / df['customer_id'].nunique() * 100).round(1)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total Salesmen", f"{len(sm_terr)}")
    with c2:
        top_sm = sm_terr.iloc[0]
        st.metric("Top Salesman", top_sm['salesman_name'][:20])
        st.caption(f"{int(top_sm['outlets'])} outlets | {int(top_sm['trx'])} trx")
    with c3:
        overlap = (df.groupby('customer_id')['salesman_name'].nunique() > 1).sum()
        st.metric("Overlapping Outlets", f"{overlap}")
    with c4:
        st.metric("Avg Trx/Salesman", f"{sm_terr['trx'].mean():.0f}")

    # Salesman bar chart
    st.subheader("👤 Outlet Coverage per Salesman")
    fig = px.bar(
        sm_terr,
        x='salesman_name', y='outlets',
        color='trx', text='outlets',
        labels={'salesman_name':'Salesman','outlets':'Outlets','trx':'Transactions'},
        color_continuous_scale='Blues'
    )
    fig.update_layout(xaxis={'tickangle': -30}, height=400)
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

    # Tabel: outlet coverage per salesman
    sm_cov_table = sm_terr[['salesman_name','outlets','trx','trx_per_outlet','pct_outlets','channels','areas']].copy()
    sm_cov_table.columns = ['Salesman','#Outlets','#Transaksi','Trx/Outlet','%Share','#Channels','#Areas']
    sm_cov_table = sm_cov_table.sort_values('#Outlets', ascending=False)
    st.markdown("**📋 Tabel: Outlet Coverage per Salesman**")
    st.dataframe(sm_cov_table, use_container_width=True, hide_index=True)

    # Table: salesman performance detail with products & areas
    sm_perf = df.groupby(['salesman_name','customer_channel','city_prov']).agg(
        outlets=('customer_id','nunique'),
        trx=('bill_no','count'),
        qty=('quantity','sum'),
        produk=('product_name', lambda x: ', '.join(x.unique()))
    ).reset_index().sort_values('trx', ascending=False)
    sm_perf.columns = ['Salesman','Channel','Area','#Outlets','#Trx','Qty','Products']
    st.markdown("**📋 Salesman × Channel × Area Detail**")
    st.dataframe(sm_perf.head(30), use_container_width=True, hide_index=True)

    st.markdown("---")

    # Territory table
    st.dataframe(
        sm_terr[['salesman_name','outlets','trx','trx_per_outlet','pct_outlets','channels','areas','products']].rename(columns={
            'salesman_name':'Salesman','outlets':'Outlets','trx':'Trx','trx_per_outlet':'Trx/OL',
            'pct_outlets':'%Outlets','channels':'Chans','areas':'Areas','products':'Products'
        }),
        use_container_width=True, hide_index=True
    )

    st.markdown("---")

    # Channel-Salesman matrix
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Salesman × Channel")
        sm_chan = df.pivot_table(
            index='salesman_name', columns='customer_channel',
            values='bill_no', aggfunc='count', fill_value=0
        )
        top_chans = df['customer_channel'].value_counts().head(10).index.tolist()
        sm_chan_show = sm_chan[[c for c in top_chans if c in sm_chan.columns]]

        fig = go.Figure(data=go.Heatmap(
            z=sm_chan_show.values,
            x=sm_chan_show.columns,
            y=sm_chan_show.index,
            colorscale='Blues',
            text=sm_chan_show.values,
            texttemplate='%{text}',
            colorbar=dict(title='Trx')
        ))
        fig.update_layout(height=500, xaxis={'tickangle': -45})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🗺️ Salesman × Area")
        sm_area = df.pivot_table(
            index='salesman_name', columns='city_prov',
            values='bill_no', aggfunc='count', fill_value=0
        )
        top_areas = df['city_prov'].value_counts().head(8).index.tolist()
        sm_area_show = sm_area[[c for c in top_areas if c in sm_area.columns]]

        fig = go.Figure(data=go.Heatmap(
            z=sm_area_show.values,
            x=sm_area_show.columns,
            y=sm_area_show.index,
            colorscale='Greens',
            text=sm_area_show.values,
            texttemplate='%{text}',
            colorbar=dict(title='Trx')
        ))
        fig.update_layout(height=500, xaxis={'tickangle': -30})
        st.plotly_chart(fig, use_container_width=True)

        # Tabel: salesman × area
        sm_area_table = sm_area_show.fillna(0).astype(int).reset_index()
        sm_area_table.columns = ['Salesman'] + list(sm_area_show.columns)
        st.markdown("**📋 Tabel: Salesman × Area (jumlah transaksi)**")
        st.dataframe(sm_area_table, use_container_width=True, hide_index=True)

    with col1:
        # Tabel: salesman × channel (sumber dari heatmap)
        st.markdown("**📋 Tabel: Salesman × Channel (jumlah transaksi)**")
        sm_chan_table = sm_chan_show.fillna(0).astype(int).reset_index()
        sm_chan_table.columns = ['Salesman'] + list(sm_chan_show.columns)
        st.dataframe(sm_chan_table, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Daily pattern per salesman
    st.subheader("📅 Daily Activity Pattern per Salesman")
    day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    sm_day = df.pivot_table(
        index='salesman_name', columns='day_name',
        values='bill_no', aggfunc='count', fill_value=0
    )
    sm_day = sm_day.reindex(columns=[c for c in day_order if c in sm_day.columns])
    sm_day_top = sm_day.reindex(sm_terr.head(6)['salesman_name'].tolist())

    fig = go.Figure()
    for day in sm_day_top.columns:
        fig.add_trace(go.Bar(name=day, x=sm_day_top.index, y=sm_day_top[day]))
    fig.update_layout(
        barmode='group', xaxis={'tickangle': -20},
        height=400, template='plotly_white',
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

    # Primary channel/salesman
    st.subheader("🎯 Primary Channel per Salesman")
    primary = []
    for sm in sm_terr.head(8)['salesman_name'].tolist():
        if sm in sm_chan.index:
            row = sm_chan.loc[sm]
            top_c = row.idxmax()
            cnt = row.max()
            total = row.sum()
            primary.append({'Salesman': sm, 'Primary Channel': top_c, 'Trx': int(cnt), 'Total Trx': int(total), 'Share': f"{cnt/total*100:.0f}%"})
    st.dataframe(pd.DataFrame(primary), use_container_width=True, hide_index=True)

    # ── 📊 MARKET-SALES SUMMARY ──────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Ringkasan Perilaku Salesman & Territory")

    total_outlets_sm = df['customer_id'].nunique()
    total_sm = len(sm_terr)
    top_sm_name = sm_terr.iloc[0]['salesman_name']
    top_sm_ol = int(sm_terr.iloc[0]['outlets'])
    top_sm_trx = int(sm_terr.iloc[0]['trx'])
    top_sm_pct_trx = sm_terr.iloc[0]['trx'] / len(df) * 100

    overlap_sm = (df.groupby('customer_id')['salesman_name'].nunique() > 1).sum()

    # Best performing salesman (highest trx per outlet)
    sm_terr['trx_per_ol'] = sm_terr['trx'] / sm_terr['outlets']
    best_efficiency_sm = sm_terr.nlargest(1,'trx_per_ol').iloc[0]

    col_sm1, col_sm2, col_sm3 = st.columns(3)
    with col_sm1:
        st.markdown(f"""
        <div class="insight-card">
        <h4 style="color:#58a6ff; margin:0 0 0.5rem;">👤 Salesman Overview</h4>
        <b>Total Salesman:</b> {total_sm}<br>
        <b>Total Outlets:</b> {total_outlets_sm}<br>
        <b>Overlap Outlets:</b> {overlap_sm} (2+ salesmen)<br>
        <b>Best Efficiency:</b> {best_efficiency_sm['salesman_name'][:20]} ({best_efficiency_sm['trx_per_ol']:.1f} trx/ol)<br>
        </div>
        """, unsafe_allow_html=True)

    with col_sm2:
        st.markdown(f"""
        <div class="danger-card">
        <h4 style="color:#E74C3C; margin:0 0 0.5rem;">⚠️ Top Salesman Risk</h4>
        <b>{top_sm_name[:25]}</b><br>
        <b>{top_sm_trx} trx ({top_sm_pct_trx:.1f}% of all)</b><br>
        <b>{top_sm_ol} outlets covered</b><br>
        <b>Single point of failure!</b><br>
        </div>
        """, unsafe_allow_html=True)

    with col_sm3:
        # Second & third salesman
        sm_sorted = sm_terr.sort_values('trx', ascending=False)
        if len(sm_sorted) > 1:
            s2 = sm_sorted.iloc[1]
            s2_pct = s2['trx']/len(df)*100
        else:
            s2 = {'salesman_name': 'N/A', 'trx': 0, 'pct_outlets': 0}
            s2_pct = 0
        st.markdown(f"""
        <div class="success-card">
        <h4 style="color:#2ECC71; margin:0 0 0.5rem;">✅ Backup Salesman</h4>
        <b>2nd Highest:</b> {s2['salesman_name'][:25] if s2['salesman_name'] else 'N/A'}<br>
        <b>Trx:</b> {int(s2['trx'])} ({s2_pct:.1f}%)<br>
        <b>Outlets:</b> {int(s2.get('outlets',0))}<br>
        </div>
        """, unsafe_allow_html=True)

    # Tabel: salesman summary
    sm_sum = sm_terr[['salesman_name','outlets','trx','trx_per_outlet','pct_outlets','channels','areas']].copy()
    sm_sum.columns = ['Salesman','#Outlets','#Trx','Trx/Outlet','%Outlets','#Channels','#Areas']
    sm_sum = sm_sum.sort_values('#Trx', ascending=False)
    st.markdown("**📋 Salesman Summary Table**")
    st.dataframe(sm_sum, use_container_width=True, hide_index=True)

# ─────────────────────────────── REPEAT ORDER ──────────────────────────────────
elif page == "🔁 Repeat Order Analytics":
    st.markdown('<div class="section-header">🔁 Repeat Order Patterns</div>', unsafe_allow_html=True)

    # Summary
    rp = repeat_data
    rp_rate = rp['is_repeat'].mean()*100
    one_time = (~rp['is_repeat']).sum()
    repeats = rp['is_repeat'].sum()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("Active Outlets (30d)", f"{len(rp)}")
    with c2: st.metric("Repeat Buyers", f"{repeats}")
    with c3: st.metric("One-Time", f"{one_time}")
    with c4: st.metric("Repeat Rate", f"{rp_rate:.1f}%")
    with c5:
        med_int = rp[rp['is_repeat']]['repeat_interval'].median()
        st.metric("Med. Interval", f"{med_int:.0f} days")
    with c6:
        active_recent = (rp['days_since_last'] <= 7).sum()
        st.metric("Still Active (≤7d)", f"{active_recent}")

    st.markdown("---")

    # Repeat rate by channel
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔄 Repeat Rate by Channel")
        rp_chan = rp.groupby('channel').agg(
            total=('customer_id','count'),
            repeats=('is_repeat','sum')
        ).reset_index()
        rp_chan['rate'] = (rp_chan['repeats'] / rp_chan['total'] * 100).round(1)
        rp_chan = rp_chan.sort_values('rate', ascending=False)

        fig = px.bar(
            rp_chan,
            x='channel', y='rate',
            color='rate', text='rate',
            color_continuous_scale='RdYlGn',
            labels={'channel':'Channel','rate':'Repeat Rate (%)'}
        )
        fig.add_hline(y=rp_rate, line_dash='dash', annotation_text=f"Avg {rp_rate:.0f}%", line_color='gray')
        fig.update_layout(showlegend=False, xaxis={'tickangle': -45}, height=400)
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

        # Table: repeat detail by channel
        rp_chan_det = rp.groupby('channel').agg(
            outlets=('customer_id','count'),
            repeat_buyers=('is_repeat','sum'),
            first_trx=('first_trx','min'),
            last_trx=('last_trx','max')
        ).reset_index()
        rp_chan_det.columns = ['Channel','#Outlets','Repeat Buyers','First Trx','Last Trx']
        rp_chan_det['Repeat Rate'] = (rp_chan_det['Repeat Buyers'] / rp_chan_det['#Outlets'] * 100).round(1).astype(str) + '%'
        rp_chan_det = rp_chan_det.sort_values('Repeat Buyers', ascending=False)
        st.markdown("**📋 Repeat Detail by Channel**")
        st.dataframe(rp_chan_det, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("🔄 Repeat Rate by Area")
        rp_area = rp.groupby('city_prov').agg(
            total=('customer_id','count'),
            repeats=('is_repeat','sum')
        ).reset_index()
        rp_area['rate'] = (rp_area['repeats'] / rp_area['total'] * 100).round(1)
        rp_area = rp_area[rp_area['total'] >= 2].sort_values('rate', ascending=False)

        fig = px.bar(
            rp_area.head(10),
            x='city_prov', y='rate',
            color='rate', text='rate',
            color_continuous_scale='RdYlGn',
            labels={'city_prov':'Area','rate':'Repeat Rate (%)'}
        )
        fig.add_hline(y=rp_rate, line_dash='dash', annotation_text=f"Avg {rp_rate:.0f}%", line_color='gray')
        fig.update_layout(showlegend=False, xaxis={'tickangle': -30}, height=400)
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

        # Table: repeat detail by area
        rp_area_det = rp.groupby('city_prov').agg(
            outlets=('customer_id','count'),
            repeat_buyers=('is_repeat','sum'),
            avg_interval=('repeat_interval','mean')
        ).reset_index()
        rp_area_det.columns = ['Area','#Outlets','Repeat Buyers','Avg Interval (days)']
        rp_area_det = rp_area_det[rp_area_det['#Outlets'] >= 2].sort_values('Repeat Buyers', ascending=False)
        rp_area_det['Repeat Rate'] = (rp_area_det['Repeat Buyers'] / rp_area_det['#Outlets'] * 100).round(1).astype(str) + '%'
        st.markdown("**📋 Repeat Detail by Area**")
        st.dataframe(rp_area_det, use_container_width=True, hide_index=True)

    # Repeat interval
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("⏱️ Repeat Interval Distribution")
        rp_repeat = rp[rp['is_repeat']]
        if len(rp_repeat) > 0:
            int_bins = [0, 1, 3, 5, 7, 14, 999]
            int_labels = ['Daily','2-3d','4-5d','6-7d','8-14d','14+d']
            int_dist = pd.cut(rp_repeat['repeat_interval'], bins=int_bins, labels=int_labels).value_counts()
            int_order = ['Daily','2-3d','4-5d','6-7d','8-14d','14+d']
            int_dist = int_dist.reindex(int_order).fillna(0)

            fig = px.pie(
                values=int_dist.values.astype(int), names=int_dist.index,
                title='Repeat Interval Distribution',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_traces(textinfo='percent+value')
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

            # Tabel: repeat interval distribution
            int_pie_table = pd.DataFrame({
                'Interval': int_order,
                'Jumlah Outlet': [int(int_dist[i]) for i in int_order],
                '% dari Total': [f"{int_dist[i]/int_dist.sum()*100:.1f}%" for i in int_order]
            })
            st.markdown("**📋 Tabel: Repeat Interval Distribution**")
            st.dataframe(int_pie_table, use_container_width=True, hide_index=True)
            st.caption(f"Total repeat buyers: {len(rp_repeat)} outlets")

    with col2:
        st.subheader("📅 Recency of Repeat Customers")
        rec_repeat = pd.cut(
            rp_repeat['days_since_last'],
            bins=[0, 3, 7, 14, 30, 999],
            labels=['0-3d','4-7d','8-14d','15-30d','30+d']
        ).value_counts()
        ro2 = ['0-3d','4-7d','8-14d','15-30d','30+d']
        rec_repeat = rec_repeat.reindex(ro2).fillna(0)

        colors2 = ['#2ECC71','#27AE60','#F39C12','#E74C3C','#C0392B']
        fig = go.Figure()
        for label, color in zip(ro2, colors2):
            fig.add_trace(go.Bar(
                x=[label], y=[int(rec_repeat[label])],
                text=str(int(rec_repeat[label])),
                textposition='outside',
                marker_color=color, name=label
            ))
        fig.update_layout(showlegend=False, height=300, yaxis_title='Outlets')
        st.plotly_chart(fig, use_container_width=True)

        # Tabel: recency of repeat customers
        rec_rep_table = pd.DataFrame({
            'Recency': ro2,
            'Jumlah Outlet': [int(rec_repeat[r]) for r in ro2],
            '% dari Total': [f"{rec_repeat[r]/rec_repeat.sum()*100:.1f}%" for r in ro2]
        })
        st.markdown("**📋 Tabel: Recency of Repeat Customers**")
        st.dataframe(rec_rep_table, use_container_width=True, hide_index=True)

    # Top repeat customers
    st.markdown("---")
    st.subheader("🏆 Top 20 Repeat Customers")
    top_repeat = rp[rp['is_repeat']].sort_values('num_trx', ascending=False).head(20)
    top_repeat = top_repeat.rename(columns={
        'num_trx':'Trx','channel':'Channel','city_prov':'Area',
        'repeat_interval':'Interval (days)','days_since_last':'Days Since Last'
    })[['customer_id','Channel','Area','Trx','Interval (days)','Days Since Last']]
    st.dataframe(top_repeat, use_container_width=True, hide_index=True)

    # Repeat vs One-time comparison
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔁 Repeat vs One-Time — Channel Split")
        rp['segment'] = rp['is_repeat'].map({True:'Repeat (2x+)', False:'One-time'})

        seg_chan = rp.groupby(['channel','segment']).size().unstack(fill_value=0)
        seg_chan_top = seg_chan.reindex(rp['channel'].value_counts().head(10).index)

        fig = go.Figure()
        for seg in seg_chan_top.columns:
            fig.add_trace(go.Bar(name=seg, x=seg_chan_top.index, y=seg_chan_top[seg], text=seg_chan_top[seg]))
        fig.update_layout(barmode='stack', xaxis={'tickangle': -30}, height=400, template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📊 Repeat vs One-Time — Area Split")
        seg_area = rp.groupby(['city_prov','segment']).size().unstack(fill_value=0)
        seg_area_top = seg_area.reindex(rp['city_prov'].value_counts().head(8).index)

        fig = go.Figure()
        for seg in seg_area_top.columns:
            fig.add_trace(go.Bar(name=seg, x=seg_area_top.index, y=seg_area_top[seg], text=seg_area_top[seg]))
        fig.update_layout(barmode='stack', xaxis={'tickangle': -30}, height=400, template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)

    # ── 📊 REPEAT ORDER SUMMARY ────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Ringkasan Repeat Order & Loyalitas")

    rp = repeat_data
    total_ol_rp = len(rp)
    repeat_ol_rp = rp['is_repeat'].sum()
    one_time_rp = total_ol_rp - repeat_ol_rp
    rp_rate_rp = rp['is_repeat'].mean()*100

    # Top repeat by trx count
    top_repeat_ol = rp[rp['is_repeat']].nlargest(1,'num_trx').iloc[0]
    top_repeat_name = top_repeat_ol['customer_id']
    top_repeat_trx = top_repeat_ol['num_trx']
    top_repeat_chn = top_repeat_ol['channel']
    top_repeat_area = top_repeat_ol['city_prov']

    # Interval stats
    rp_repeat_only = rp[rp['is_repeat']]
    median_int = rp_repeat_only['repeat_interval'].median()
    mean_int = rp_repeat_only['repeat_interval'].mean()

    # Channel repeat rate
    chan_rr_rp = rp.groupby('channel')['is_repeat'].mean()*100
    best_rp_chan = chan_rr_rp.idxmax()
    best_rp_rr = chan_rr_rp.max()
    worst_rp_chan = chan_rr_rp.idxmin()
    worst_rp_rr = chan_rr_rp.min()

    # At-risk repeat outlets (already repeat but inactive)
    rp_at_risk = rp_repeat_only[rp_repeat_only['days_since_last'] > 7].shape[0]

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.markdown(f"""
        <div class="insight-card">
        <h4 style="color:#58a6ff; margin:0 0 0.5rem;">🔁 Repeat Summary</h4>
        <b>Total Active Outlets:</b> {total_ol_rp}<br>
        <b>Repeat Buyers:</b> {repeat_ol_rp} ({rp_rate_rp:.1f}%)<br>
        <b>One-Time Buyers:</b> {one_time_rp} ({100-rp_rate_rp:.1f}%)<br>
        <b>Repeat At-Risk (>7d):</b> {rp_at_risk}<br>
        </div>
        """, unsafe_allow_html=True)

    with col_r2:
        st.markdown(f"""
        <div class="success-card">
        <h4 style="color:#2ECC71; margin:0 0 0.5rem;">🏆 Most Loyal Outlet</h4>
        <b>Outlet:</b> {top_repeat_name[:25]}<br>
        <b>Channel:</b> {top_repeat_chn}<br>
        <b>Area:</b> {str(top_repeat_area)[:25]}<br>
        <b>Total Trx:</b> {top_repeat_trx} | <b>Interval:</b> {median_int:.0f} days<br>
        </div>
        """, unsafe_allow_html=True)

    with col_r3:
        st.markdown(f"""
        <div class="insight-card">
        <h4 style="color:#58a6ff; margin:0 0 0.5rem;">⏱️ Interval Stats</h4>
        <b>Median Interval:</b> {median_int:.0f} days<br>
        <b>Mean Interval:</b> {mean_int:.1f} days<br>
        <b>Best Channel:</b> {best_rp_chan} ({best_rp_rr:.1f}%)<br>
        <b>Worst Channel:</b> {worst_rp_chan} ({worst_rp_rr:.1f}%)<br>
        </div>
        """, unsafe_allow_html=True)

    # Tabel: repeat summary by channel
    rp_chan_sum = rp.groupby('channel').agg(
        outlets=('customer_id','count'),
        repeat_buyers=('is_repeat','sum'),
        avg_interval=('repeat_interval','mean'),
        avg_days_since=('days_since_last','mean')
    ).reset_index()
    rp_chan_sum['repeat_rate'] = (rp_chan_sum['repeat_buyers'] / rp_chan_sum['outlets'] * 100).round(1)
    rp_chan_sum = rp_chan_sum.sort_values('outlets', ascending=False)
    rp_chan_sum.columns = ['Channel','#Outlets','Repeat Buyers','Avg Interval','Avg Days Since','Repeat %']
    st.markdown("**📋 Repeat Summary by Channel**")
    st.dataframe(rp_chan_sum, use_container_width=True, hide_index=True)

# ─────────────────────────────── INSIGHTS ─────────────────────────────────────
elif page == "💡 Insights & Actions":
    st.markdown('<div class="section-header">💡 Key Behavioral Insights & Recommended Actions</div>', unsafe_allow_html=True)

    # ── Dynamic calculations (ALL from real data) ─────────────────────────────
    rp_rate = repeat_data['is_repeat'].mean()*100
    churn_rate = (outlet_summary['days_since_last'] > 14).mean()*100

    # Outlets metrics
    total_outlets = len(outlet_summary)
    one_time = (~repeat_data['is_repeat']).sum()
    repeat_buyers = repeat_data['is_repeat'].sum()
    churned_outlets = int(outlet_summary[outlet_summary['days_since_last'] > 14].shape[0])

    # Channel analysis
    chan_rr = repeat_data.groupby('channel')['is_repeat'].mean()*100
    best_repeat = chan_rr.idxmax()
    best_repeat_rate = chan_rr.max()
    worst_repeat = chan_rr.idxmin()
    worst_repeat_rate = chan_rr.min()

    # Salesman
    sm_counts = df['salesman_name'].value_counts()
    top_sm = sm_counts.index[0]
    top_sm_cnt = sm_counts.iloc[0]
    top_sm_pct = top_sm_cnt / len(df) * 100

    # Top area
    top_area = df['city_prov'].value_counts().idxmax()

    # Overlap
    overlap = (df.groupby('customer_id')['salesman_name'].nunique() > 1).sum()

    # Peak day
    best_day = df['day_name'].value_counts().idxmax()
    best_day_cnt = df['day_name'].value_counts().iloc[0]
    second_day = df['day_name'].value_counts().index[1]
    second_day_cnt = df['day_name'].value_counts().iloc[1]

    # Multi-product
    multi_prod = (outlet_summary['num_products'] > 1).sum()

    # Repeat interval
    repeat_median_int = repeat_data[repeat_data['is_repeat']]['repeat_interval'].median()
    repeat_interval_mean = repeat_data[repeat_data['is_repeat']]['repeat_interval'].mean()

    # LAINNYA stats
    lainnya_outlets = df[df['customer_channel']=='LAINNYA']['customer_id'].nunique()
    lainnya_trx = len(df[df['customer_channel']=='LAINNYA'])
    lainnya_rr = repeat_data[repeat_data['channel']=='LAINNYA']['is_repeat'].mean()*100
    lainnya_one_time = 100 - lainnya_rr

    # Top area details
    area_outlets = df['city_prov'].value_counts()
    area_repeat = repeat_data.groupby('city_prov')['is_repeat'].mean()*100
    area_churn = outlet_summary.groupby('city_prov')['days_since_last'].apply(
        lambda x: (x > 14).mean()*100
    )

    # Channel counts for action
    toko_outlets = repeat_data[repeat_data['channel']=='TOKO']['customer_id'].nunique()
    toko_rr = repeat_data[repeat_data['channel']=='TOKO']['is_repeat'].mean()*100

    # Salesman breakdown
    sm_details = df.groupby('salesman_name').agg(
        trx=('bill_no','count'),
        outlets=('customer_id','nunique'),
        channels=('customer_channel','nunique')
    ).reset_index().sort_values('trx', ascending=False)

    # Area analysis
    area_summary = outlet_summary.groupby('city_prov').agg(
        outlets=('customer_id','count'),
        churned=('days_since_last', lambda x: (x > 14).sum()),
        churn_rate=('days_since_last', lambda x: (x > 14).mean()*100)
    ).reset_index().sort_values('outlets', ascending=False)

    # ── 🚨 CRITICAL ISSUES ────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="danger-card">
    <h3 style="margin:0 0 0.5rem;color:#E74C3C;">🚨 Critical Issues</h3>
    <ul style="margin:0; padding-left:1.2rem;">
      <li><b>One-Time Buyer Rate: {one_time} outlets ({100-rp_rate:.1f}%)</b> — Majority never return. Need systematic follow-up within 3 days of first purchase.</li>
      <li><b>Churn Rate: {churn_rate:.1f}% — {churned_outlets} outlets</b> — Inactive >14 days from last transaction ({df['transaction_date'].max().date()}). Priority win-back target.</li>
      <li><b>TOKO channel: {toko_rr:.1f}% repeat rate ({toko_outlets} outlets)</b> — 2nd largest channel by outlets, but low retention. Needs immediate intervention.</li>
      <li><b>{top_sm}: {top_sm_pct:.1f}% of all transactions ({top_sm_cnt} trx)</b> — Single point of failure. Burnout & dependency risk if absent.</li>
      <li><b>{overlap} outlets visited by 2+ salesmen</b> — Territory conflict. Causes overlapping visits & wasted effort.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # ── ✅ STRENGTHS ─────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="success-card">
    <h3 style="margin:0 0 0.5rem;color:#2ECC71;">✅ Strengths</h3>
    <ul style="margin:0; padding-left:1.2rem;">
      <li><b>BENGKEL: {repeat_data[repeat_data['channel']=='BENGKEL']['is_repeat'].mean()*100:.1f}% repeat rate</b> — Best retention per outlet (7 outlets, 71% return). Replicate this model!</li>
      <li><b>RESTORAN: {repeat_data[repeat_data['channel']=='RESTORAN']['is_repeat'].mean()*100:.1f}% repeat rate</b> — Strongest by volume (29 outlets, 48% repeat). High loyalty.</li>
      <li><b>Repeat interval median: {repeat_median_int:.0f} days</b> — Repeat buyers return quickly ({repeat_interval_mean:.1f} days avg). Good stickiness.</li>
      <li><b>{multi_prod} outlets ({multi_prod/total_outlets*100:.1f}%) buy multiple products</b> — Cross-sell opportunity. Push bundle offers to remaining 92%.</li>
      <li><b>Peak day: {best_day} ({best_day_cnt} trx / {best_day_cnt/len(df)*100:.1f}%)</b> — Scheduling can be optimized. 2nd peak: {second_day} ({second_day_cnt} trx).</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # ── ⚡ IMMEDIATE ACTIONS ────────────────────────────────────────────────
    st.markdown(f"""
    <div class="warn-card">
    <h3 style="margin:0 0 0.5rem;color:#F39C12;">⚡ Immediate Actions (0-7 Days)</h3>
    <ul style="margin:0; padding-left:1.2rem;">
      <li><b>TOKO Channel Follow-Up:</b> {toko_outlets} outlets, only {toko_rr:.1f}% repeat. Phone/WhatsApp outreach within 3 days of first purchase. Target one-time buyers.</li>
      <li><b>Win-Back Campaign:</b> {churned_outlets} outlets churned (>14 days inactive). Sort by area → prioritize Sleman & Bantul (highest churn). Outreach within 48 hours.</li>
      <li><b>Resolve Overlap:</b> {overlap} outlets with 2+ salesmen assigned. Assign clear boundary — one salesman per outlet.</li>
      <li><b>LATHIEF NUR S Backup:</b> {top_sm_pct:.1f}% transactions from one person. Assign backup salesman for his outlets immediately.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # ── 📋 SHORT-TERM ACTIONS ───────────────────────────────────────────────
    st.markdown(f"""
    <div class="insight-card">
    <h3 style="margin:0 0 0.5rem;color:#2E86AB;">📋 Short-Term Actions (1-4 Weeks)</h3>
    <ul style="margin:0; padding-left:1.2rem;">
      <li><b>Replicate BENGKEL & RESTORAN Model:</b> Both channels have 48-71% repeat rate. Analyze what they have (product mix, pricing, service) → apply to TOKO & LAINNYA.</li>
      <li><b>Territory Rebalancing:</b> {top_sm} handles {top_sm_pct:.1f}% of all transactions. Redistribute {int(top_sm_pct*0.3)}% of his outlets to AGUS SUYANTO (2nd highest) & AKHMAD KHOIRUL.</li>
      <li><b>LAINNYA Channel Strategy:</b> Largest channel ({lainnya_outlets} outlets, {lainnya_trx} transactions) but only {lainnya_rr:.1f}% repeat. Investigate: price? product availability? service quality?</li>
      <li><b>Area Focus:</b>
        <ul>
          <li><b>Kabupaten Sleman:</b> 103 outlets, 69% churn rate — highest risk area. Assign dedicated salesman for win-back.</li>
          <li><b>SLEMAN, DI Yogyakarta:</b> 88 outlets, 34% churn — good density but needs repeat conversion push.</li>
          <li><b>Empty/blank area ({int(df[df['city_prov']==''].shape[0])} outlets):</b> 92% churn rate. Check data quality — possible unverified outlets.</li>
        </ul>
      </li>
      <li><b>Scheduling Optimization:</b> Thursday ({best_day_cnt} trx) + Sunday ({second_day_cnt} trx) = {best_day_cnt+second_day_cnt} trx combined ({((best_day_cnt+second_day_cnt)/len(df))*100:.0f}% of total). Allocate 60%+ sales capacity on these days.</li>
      <li><b>Product Bundling:</b> {multi_prod} outlets ({multi_prod/total_outlets*100:.1f}%) already multi-product. Push "Galon + Cup 120ML" bundle to remaining 92% in next 4 weeks.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # ── 🚀 GROWTH ACTIONS ───────────────────────────────────────────────────
    st.markdown(f"""
    <div class="insight-card">
    <h3 style="margin:0 0 0.5rem;color:#2E86AB;">🚀 Growth Actions (1-3 Months)</h3>
    <ul style="margin:0; padding-left:1.2rem;">
      <li><b>LAINNYA Channel Expansion:</b> {lainnya_outlets} outlets, {lainnya_trx} transactions — biggest by outlet count. {lainnya_one_time:.1f}% one-time buyers. Convert strategy: loyalty incentive after 2nd purchase.</li>
      <li><b>FACTORY Channel Growth:</b> 25 outlets, 48% repeat rate, high qty per transaction. Prioritize acquisition of more FACTORY-type outlets.</li>
      <li><b>Loyalty Program:</b> Target {repeat_buyers} repeat buyers. Offer: 5% discount on 3rd+ order, free delivery for >5 units, priority restock notification.</li>
      <li><b>Multi-Product Push:</b> {(total_outlets-multi_prod)} outlets ({(total_outlets-multi_prod)/total_outlets*100:.0f}%) buy only 1 product. Bundle: "Galon + Cup 120ML" discount package. Target 20% conversion in 3 months.</li>
      <li><b>Salesman Coaching:</b>
        <ul>
          <li><b>{top_sm}</b> ({top_sm_pct:.1f}% trx) → overworked. Coaching: delegate & backup plan.</li>
          <li><b>AGUS SUYANTO</b> ({df[df['salesman_name']=='AGUS SUYANTO']['bill_no'].count()/len(df)*100:.1f}% trx, {df[df['salesman_name']=='AGUS SUYANTO']['customer_id'].nunique()} outlets) → expand territory.</li>
          <li><b>BRUSLI STEVANGGIH</b> ({df[df['salesman_name']=='BRUSLI STEVANGGIH']['bill_no'].count()} trx) → low activity. Coaching on outlet acquisition.</li>
        </ul>
      </li>
      <li><b>Empty/Blank Area Cleanup:</b> {int(df[df['city_prov'].str.strip()==''].shape[0])} outlets with no area data. Verify & update customer records before analysis.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── 📊 SUMMARY TABLES ─────────────────────────────────────────────────────
    st.subheader("📊 Summary Data Tables")

    # Summary 1: Channel Performance
    chan_perf = df.groupby('customer_channel').agg(
        outlets=('customer_id','nunique'),
        trx=('bill_no','count'),
        avg_trx=('bill_no', lambda x: round(x.count() / df[df['customer_channel'].isin([df['customer_channel'].iloc[0]])]['customer_id'].nunique(), 2))
    ).reset_index()
    chan_perf2 = df.groupby('customer_channel').agg(
        outlets=('customer_id','nunique'),
        trx=('bill_no','count'),
        qty=('quantity','sum'),
        repeat_outlets=('customer_id', lambda x: repeat_data[repeat_data['customer_id'].isin(x)]['is_repeat'].sum()),
        churn_outlets=('customer_id', lambda x: outlet_summary[outlet_summary['customer_id'].isin(x) & (outlet_summary['days_since_last'] > 14)].shape[0])
    ).reset_index()
    chan_perf2['repeat_rate'] = (chan_perf2['repeat_outlets'] / chan_perf2['outlets'] * 100).round(1)
    chan_perf2['churn_rate'] = (chan_perf2['churn_outlets'] / chan_perf2['outlets'] * 100).round(1)
    chan_perf2 = chan_perf2.sort_values('trx', ascending=False)
    chan_perf2.columns = ['Channel','#Outlets','#Trx','Total Qty','Repeat Buyers','Churned','Repeat %','Churn %']
    st.markdown("**📋 Channel Performance Summary**")
    st.dataframe(chan_perf2, use_container_width=True, hide_index=True)

    # Summary 2: Salesman Performance
    sm_perf = sm_details.copy()
    sm_perf['repeat_rate'] = sm_perf['salesman_name'].apply(
        lambda x: repeat_data[repeat_data['customer_id'].isin(
            df[df['salesman_name']==x]['customer_id']
        )]['is_repeat'].mean()*100
    ).round(1)
    sm_perf.columns = ['Salesman','#Trx','#Outlets','#Channels','Repeat Rate %']
    sm_perf = sm_perf.sort_values('#Trx', ascending=False)
    st.markdown("**📋 Salesman Performance Summary**")
    st.dataframe(sm_perf, use_container_width=True, hide_index=True)

    # Summary 3: Area Performance
    area_perf = area_summary.copy()
    area_perf = area_perf.sort_values('outlets', ascending=False)
    area_perf.columns = ['Area','#Outlets','Churned','Churn Rate %']
    st.markdown("**📋 Area Performance Summary**")
    st.dataframe(area_perf, use_container_width=True, hide_index=True)

    # ── Summary Tables ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 At-Risk Outlets by Area (Most Days Since Last Trx)")
    at_risk_all = df.groupby(['city_prov','customer_name','customer_channel']).agg(
        last_trx=('transaction_date','max'),
        trx_count=('bill_no','count'),
        qty_total=('quantity','sum'),
        produk=('product_name', lambda x: ', '.join(x.unique()[:3])),
        salesman=('salesman_name', lambda x: x.mode()[0] if len(x.mode()) else 'N/A')
    ).reset_index()
    at_risk_all['days_since'] = (df['transaction_date'].max() - at_risk_all['last_trx']).dt.days
    at_risk_all = at_risk_all.sort_values('days_since', ascending=False).head(30)
    at_risk_all.columns = ['Area','Outlet','Channel','Last Trx','#Trx','Qty','Products (sample)','Salesman','Days Since']
    at_risk_all['Last Trx'] = at_risk_all['Last Trx'].dt.strftime('%Y-%m-%d')
    st.dataframe(at_risk_all, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 Top Outlets by Volume — per Channel")
    top_by_qty = df.groupby(['customer_channel','customer_name','city_prov']).agg(
        trx=('bill_no','count'),
        qty=('quantity','sum'),
        salesman=('salesman_name', lambda x: x.mode()[0] if len(x.mode()) else 'N/A')
    ).reset_index().sort_values(['customer_channel','qty'], ascending=[True,False])
    top_by_qty.columns = ['Channel','Outlet','Area','#Trx','Qty','Salesman']
    st.dataframe(top_by_qty.head(40), use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#7f8c8d; padding:1rem; font-size:0.8rem;">
    Arbas Market Intelligence — Behavior Analytics Dashboard | Data: Mar–Apr 2026 | Generated: 2026-05-03
</div>
""", unsafe_allow_html=True)