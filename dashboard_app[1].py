
"""
🎯 ARBAS MARKET INTELLIGENCE DASHBOARD
Sales & Distribution Analytics
=====================================

Run: streamlit run dashboard_app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Arbas Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ──────────────────────────────���──────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E86AB;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #2E86AB 0%, #2ECC71 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #2E86AB;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #7f8c8d;
        text-transform: uppercase;
    }
    .insight-box {
        background: #f8f9fa;
        padding: 1rem;
        border-left: 4px solid #2E86AB;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3cd;
        padding: 1rem;
        border-left: 4px solid #F39C12;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .danger-box {
        background: #f8d7da;
        padding: 1rem;
        border-left: 4px solid #E74C3C;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .success-box {
        background: #d4edda;
        padding: 1rem;
        border-left: 4px solid #2ECC71;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Load Data ───────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("master_sales_analysis.csv")

    # Feature engineering
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])
    df['delivery_date'] = pd.to_datetime(df['delivery_date'])
    df['day_name'] = df['transaction_date'].dt.day_name()
    df['date_only'] = df['transaction_date'].dt.date
    df['month'] = df['transaction_date'].dt.month
    df['week'] = df['transaction_date'].dt.isocalendar().week

    # Province extraction
    df['city_prov_clean'] = df['customer_city_prov'].str.strip()
    df['province'] = df['city_prov_clean'].str.extract(r',\s*(.+)$')[0].fillna('Unknown')

    return df

@st.cache_data
def load_rfm_segments():
    return pd.read_csv("rfm_segments.csv")

@st.cache_data
def load_churned_outlets():
    return pd.read_csv("churned_outlets.csv")

@st.cache_data
def load_repeat_customers():
    return pd.read_csv("repeat_order_customers.csv")

@st.cache_data
def load_sales_performance():
    return pd.read_csv("sales_performance.csv")

df = load_data()
rfm = load_rfm_segments()
churned = load_churned_outlets()
repeat_customers = load_repeat_customers()
sales_perf = load_sales_performance()

# ── Sidebar Filters ────────────────────────────────────────────────────────────
st.sidebar.title("📊 Dashboard Filters")

date_range = st.sidebar.date_input(
    "Date Range",
    value=(df['transaction_date'].min().date(), df['transaction_date'].max().date()),
    min_value=df['transaction_date'].min().date(),
    max_value=df['transaction_date'].max().date()
)

if len(date_range) == 2:
    start_date, end_date = date_range
    df_filtered = df[
        (df['transaction_date'].dt.date >= start_date) &
        (df['transaction_date'].dt.date <= end_date)
    ]
else:
    df_filtered = df

selected_salesman = st.sidebar.multiselect(
    "Salesman",
    options=['All'] + df['salesman_name'].unique().tolist(),
    default=['All']
)

if 'All' not in selected_salesman:
    df_filtered = df_filtered[df_filtered['salesman_name'].isin(selected_salesman)]

selected_channel = st.sidebar.multiselect(
    "Channel",
    options=['All'] + df['customer_channel'].unique().tolist(),
    default=['All']
)

if 'All' not in selected_channel:
    df_filtered = df_filtered[df_filtered['customer_channel'].isin(selected_channel)]

selected_product = st.sidebar.multiselect(
    "Product",
    options=['All'] + df['product_name'].unique().tolist(),
    default=['All']
)

if 'All' not in selected_product:
    df_filtered = df_filtered[df_filtered['product_name'].isin(selected_product)]

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-header">Arbas Market Intelligence Dashboard</div>', unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric(label="Total Revenue", value=f"Rp {df_filtered['total_revenue'].sum():,.0f}")
with col2:
    st.metric(label="Gross Profit", value=f"Rp {df_filtered['gross_profit'].sum():,.0f}")
with col3:
    st.metric(label="Transactions", value=f"{len(df_filtered):,}")
with col4:
    st.metric(label="Outlets", value=f"{df_filtered['customer_id'].nunique():,}")
with col5:
    st.metric(label="Margin", value=f"{(df_filtered['gross_profit'].sum()/df_filtered['total_revenue'].sum()*100):.1f}%")

st.markdown("---")

# ── Navigation ─────────────────────────────────────────────────────────────────
page = st.sidebar.radio(
    "Navigate to:",
    ["🏠 Executive Summary",
     "👥 Customer Analytics",
     "📦 Product & Market",
     "🚚 Delivery & Operations",
     "💰 Payment & Collection",
     "📈 Sales Performance",
     "💡 Recommendations"]
)

# ── EXECUTIVE SUMMARY PAGE ────────────────────────────────────────────────────
if page == "🏠 Executive Summary":
    st.title("🏠 Executive Summary")

    # KPI Cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📊 Business Overview")
        st.info(f"""
        **Period**: {df_filtered['transaction_date'].min().date()} → {df_filtered['transaction_date'].max().date()}
        **Total Revenue**: Rp {df_filtered['total_revenue'].sum():,.0f}
        **Gross Profit**: Rp {df_filtered['gross_profit'].sum():,.0f} ({(df_filtered['gross_profit'].sum()/df_filtered['total_revenue'].sum()*100):.1f}%)
        **Transactions**: {len(df_filtered):,}
        **Active Outlets**: {df_filtered['customer_id'].nunique():,}
        """)

    with col2:
        st.subheader("⚠️ Critical Issues")
        churn_count = len(churned)
        outstanding = df_filtered[df_filtered['is_paid'] == False]['total_revenue'].sum()
        st.warning(f"""
        **Churn Rate**: {churn_count/len(rfm)*100:.1f}% ({churn_count} outlets)
        **Outstanding**: Rp {outstanding:,.0f}
        **Pending Delivery**: {len(df_filtered[df_filtered['delivery_status']=='PENDING'])} trx
        """)

    with col3:
        st.subheader("🏆 Top Performers")
        top_sales = sales_perf.iloc[0]
        st.success(f"""
        **Top Salesman**: {top_sales['salesman_name']}
        **Revenue**: Rp {top_sales['revenue']:,.0f}
        **Top Product**: {df_filtered.groupby('product_name')['total_revenue'].sum().idxmax()}
        **Revenue Share**: {(df_filtered.groupby('product_name')['total_revenue'].sum().max()/df_filtered['total_revenue'].sum()*100):.1f}%
        """)

    st.markdown("---")

    # Revenue Trend
    st.subheader("📈 Revenue Trend")
    daily_revenue = df_filtered.groupby('date_only')['total_revenue'].sum().reset_index()
    daily_revenue['date_only'] = pd.to_datetime(daily_revenue['date_only'])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_revenue['date_only'],
        y=daily_revenue['total_revenue'],
        mode='lines+markers',
        name='Revenue',
        line=dict(color='#2E86AB', width=2),
        hovertemplate='%{x}<br>Rp %{y:,.0f}<extra></extra>'
    ))

    fig.update_layout(
        title="Daily Revenue Trend",
        xaxis_title="Date",
        yaxis_title="Revenue (Rp)",
        hovermode='x unified',
        template='plotly_white',
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    # Channel & Product Distribution
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Revenue by Channel")
        channel_revenue = df_filtered.groupby('customer_channel')['total_revenue'].sum().sort_values(ascending=False)

        fig = px.bar(
            x=channel_revenue.values,
            y=channel_revenue.index,
            orientation='h',
            title="Revenue by Channel",
            color=channel_revenue.values,
            color_continuous_scale='Blues'
        )
        fig.update_xaxes(title="Revenue (Rp)")
        fig.update_yaxes(title="")
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📦 Revenue by Product")
        product_revenue = df_filtered.groupby('product_name')['total_revenue'].sum().sort_values(ascending=False)

        fig = px.pie(
            values=product_revenue.values,
            names=product_revenue.index,
            title="Revenue Share by Product",
            hole=0.4
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

# ── CUSTOMER ANALYTICS PAGE ──────────────────────────────────────────────────
elif page == "👥 Customer Analytics":
    st.title("👥 Customer Analytics")

    # RFM Segments
    st.subheader("🎯 Customer Segmentation (RFM)")
    segment_counts = rfm['segment'].value_counts()

    col1, col2 = st.columns(2)

    with col1:
        fig = px.pie(
            values=segment_counts.values,
            names=segment_counts.index,
            title="Customer Segments Distribution",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Blues
        )
        fig.update_traces(textinfo='percent+label+value')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.dataframe(
            rfm.groupby('segment').agg({
                'customer_id': 'count',
                'monetary': 'mean',
                'frequency': 'mean'
            }).round(0).rename(columns={
                'customer_id': 'Num Outlets',
                'monetary': 'Avg Revenue',
                'frequency': 'Avg Frequency'
            }),
            use_container_width=True
        )

    st.markdown("---")

    # Churn Analysis
    st.subheader("📉 Churn Analysis")
    churn_count = len(churned)
    active_count = len(rfm) - churn_count

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Active Outlets", active_count, f"{(active_count/len(rfm)*100):.1f}%")
    with col2:
        st.metric("Churned Outlets", churn_count, f"{(churn_count/len(rfm)*100):.1f}%")
    with col3:
        potential_lost = churned['monetary'].sum()
        st.metric("Potential Revenue Lost", f"Rp {potential_lost:,.0f}")

    st.markdown("<div class='danger-box'>⚠️ <strong>Top 10 Churned Outlets by Revenue Impact</strong></div>", unsafe_allow_html=True)

    top_churned = churned.sort_values('monetary', ascending=False).head(10)
    st.dataframe(
        top_churned[['customer_name', 'channel', 'recency', 'monetary', 'frequency']],
        column_config={
            'customer_name': 'Outlet Name',
            'channel': 'Channel',
            'recency': 'Days Inactive',
            'monetary': st.column_config.NumberColumn('Revenue (Rp)', format='Rp %,.0f'),
            'frequency': 'Transactions'
        },
        hide_index=True,
        use_container_width=True
    )

    st.markdown("---")

    # Repeat Order Customers
    st.subheader("🔁 Repeat Order Analysis (Last 30 Days)")
    repeat_count = len(repeat_customers)

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Repeat Customers", repeat_count)
        st.dataframe(
            repeat_customers.head(10)[['customer_name', 'channel', 'num_orders', 'total_revenue', 'repeat_interval_days']],
            column_config={
                'customer_name': 'Outlet Name',
                'channel': 'Channel',
                'num_orders': '# Orders',
                'total_revenue': st.column_config.NumberColumn('Revenue', format='Rp %,.0f'),
                'repeat_interval_days': st.column_config.NumberColumn('Avg Interval', format='%.1f days')
            },
            hide_index=True,
            use_container_width=True
        )

    with col2:
        st.subheader("Repeat by Channel")
        channel_repeat = repeat_customers.groupby('channel').agg({
            'customer_id': 'count',
            'num_orders': 'mean',
            'total_revenue': 'sum'
        }).sort_values('customer_id', ascending=False)

        fig = px.bar(
            x=channel_repeat.index,
            y=channel_repeat['customer_id'],
            title="Number of Repeat Customers by Channel",
            labels={'x': 'Channel', 'y': 'Count'}
        )
        fig.update_layout(height=400, xaxis={'tickangle': -45})
        st.plotly_chart(fig, use_container_width=True)

# ── PRODUCT & MARKET PAGE ───────────────────────────────────────────────────
elif page == "📦 Product & Market":
    st.title("📦 Product & Market Analytics")

    # Product Performance
    st.subheader("📊 Product Performance")

    product_perf = df_filtered.groupby('product_name').agg({
        'bill_no': 'count',
        'customer_id': 'nunique',
        'total_revenue': 'sum',
        'gross_profit': 'sum',
        'quantity': 'sum',
        'margin_percent': 'mean'
    }).reset_index()
    product_perf.columns = ['Product', 'Transactions', 'Outlets', 'Revenue', 'Profit', 'Quantity', 'Avg Margin']
    product_perf['Profit Margin'] = (product_perf['Profit'] / product_perf['Revenue'] * 100).round(1)

    st.dataframe(
        product_perf.sort_values('Revenue', ascending=False),
        column_config={
            'Product': st.column_config.TextColumn('Product'),
            'Transactions': st.column_config.NumberColumn('Trx'),
            'Outlets': st.column_config.NumberColumn('Outlets'),
            'Revenue': st.column_config.NumberColumn('Revenue (Rp)', format='Rp %,.0f'),
            'Profit': st.column_config.NumberColumn('Profit (Rp)', format='Rp %,.0f'),
            'Quantity': st.column_config.NumberColumn('Qty Sold'),
            'Avg Margin': st.column_config.NumberColumn('Avg Margin (%)', format='%.1f%%'),
            'Profit Margin': st.column_config.NumberColumn('Profit Margin (%)', format='%.1f%%')
        },
        hide_index=True,
        use_container_width=True
    )

    # Product Charts
    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            product_perf.sort_values('Revenue'),
            x='Revenue',
            y='Product',
            orientation='h',
            title="Revenue by Product",
            color='Revenue',
            color_continuous_scale='Blues'
        )
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            product_perf.sort_values('Profit Margin'),
            x='Profit Margin',
            y='Product',
            orientation='h',
            title="Profit Margin by Product (%)",
            color='Profit Margin',
            color_continuous_scale='Greens'
        )
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Market Share by Area
    st.subheader("🗺️ Market Share by Area")

    area_revenue = df_filtered.groupby('city_prov_clean')['total_revenue'].sum().sort_values(ascending=False)
    area_revenue_pct = (area_revenue / area_revenue.sum() * 100).round(1)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.bar(
            x=area_revenue.values,
            y=area_revenue.index,
            orientation='h',
            title="Revenue by Area",
            color=area_revenue.values,
            color_continuous_scale='Blues'
        )
        fig.update_xaxes(title="Revenue (Rp)")
        fig.update_yaxes(title="")
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Top 5 Areas")
        top_areas = pd.DataFrame({
            'Area': area_revenue.head(5).index,
            'Revenue': area_revenue.head(5).values,
            'Share %': area_revenue_pct.head(5).values
        })
        st.dataframe(
            top_areas,
            column_config={
                'Area': st.column_config.TextColumn('Area'),
                'Revenue': st.column_config.NumberColumn('Revenue (Rp)', format='Rp %,.0f'),
                'Share %': st.column_config.NumberColumn('Share %', format='%s%%')
            },
            hide_index=True,
            use_container_width=True
        )

# ── DELIVERY & OPERATIONS PAGE ──────────────────────────────────────────────
elif page == "🚚 Delivery & Operations":
    st.title("🚚 Delivery & Operations")

    # Delivery Status Overview
    st.subheader("📦 Delivery Status Overview")

    delivery_status = df_filtered.groupby('delivery_status').agg({
        'bill_no': 'count',
        'total_revenue': 'sum'
    }).reset_index()

    col1, col2, col3 = st.columns(3)

    with col1:
        delivered_count = len(df_filtered[df_filtered['is_delivered'] == True])
        st.metric("Delivered", delivered_count, f"{(delivered_count/len(df_filtered)*100):.1f}%")

    with col2:
        pending_count = len(df_filtered[df_filtered['delivery_status'] == 'PENDING'])
        st.metric("Pending", pending_count, f"{(pending_count/len(df_filtered)*100):.1f}%")

    with col3:
        avg_lead_time = df_filtered['delivery_lead_time_days'].mean()
        st.metric("Avg Lead Time", f"{avg_lead_time:.1f} days")

    # Status Chart
    col1, col2 = st.columns(2)

    with col1:
        fig = px.pie(
            values=delivery_status['bill_no'],
            names=delivery_status['delivery_status'],
            title='Delivery Status Distribution',
            hole=0.4,
            color_discrete_map={'DELIVERED': '#2ECC71', 'PENDING': '#F39C12', 'ON_DELIVERY': '#3498DB'}
        )
        fig.update_traces(textinfo='percent+label+value')
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.dataframe(
            delivery_status,
            column_config={
                'delivery_status': 'Status',
                'bill_no': '# Transactions',
                'total_revenue': st.column_config.NumberColumn('Revenue (Rp)', format='Rp %,.0f')
            },
            hide_index=True,
            use_container_width=True
        )

    st.markdown("---")

    # Delivery by Area
    st.subheader("📍 Delivery Performance by Area")

    delivery_area = df_filtered.groupby('city_prov_clean').agg({
        'delivery_lead_time_days': 'mean',
        'is_delivered': 'mean',
        'bill_no': 'count'
    }).reset_index()
    delivery_area.columns = ['Area', 'Avg Lead Time', 'Success Rate', 'Transactions']
    delivery_area['Success Rate %'] = (delivery_area['Success Rate'] * 100).round(1)
    delivery_area = delivery_area[delivery_area['Transactions'] >= 3].sort_values('Success Rate %', ascending=False)

    st.dataframe(
        delivery_area,
        column_config={
            'Area': st.column_config.TextColumn('Area'),
            'Avg Lead Time': st.column_config.NumberColumn('Lead Time (days)', format='%.1f'),
            'Success Rate %': st.column_config.NumberColumn('Success Rate %', format='%.1f%%'),
            'Transactions': st.column_config.NumberColumn('# Trx')
        },
        hide_index=True,
        use_container_width=True
    )

    st.markdown("---")

    # Scheduling Insights
    st.subheader("📅 Scheduling Insights")

    day_perf = df_filtered.groupby('day_name').agg({
        'bill_no': 'count',
        'total_revenue': 'sum',
        'customer_id': 'nunique'
    }).reset_index()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_perf['day_name'] = pd.Categorical(day_perf['day_name'], categories=day_order, ordered=True)
    day_perf = day_perf.sort_values('day_name')

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=day_perf['day_name'],
        y=day_perf['total_revenue'],
        name='Revenue',
        marker_color='#2E86AB',
        text=day_perf['total_revenue'].apply(lambda x: f"Rp {x/1000000:.1f}M"),
        textposition='outside'
    ))

    fig.update_layout(
        title="Revenue by Day of Week",
        xaxis_title="Day",
        yaxis_title="Revenue (Rp)",
        template='plotly_white',
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    best_day = day_perf.loc[day_perf['total_revenue'].idxmax()]
    st.info(f"🔥 **Best Day**: {best_day['day_name']} with Rp {best_day['total_revenue']:,.0f} revenue from {best_day['bill_no']} transactions")

# ── PAYMENT & COLLECTION PAGE ───────────────────────────────────────────────
elif page == "💰 Payment & Collection":
    st.title("💰 Payment & Collection")

    # Payment Overview
    st.subheader("💳 Payment Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        cash_count = len(df_filtered[df_filtered['payment_type'] == 'CASH'])
        st.metric("Cash Trx", cash_count, f"{(cash_count/len(df_filtered)*100):.1f}%")

    with col2:
        credit_count = len(df_filtered[df_filtered['payment_type'] == 'CREDIT'])
        st.metric("Credit Trx", credit_count, f"{(credit_count/len(df_filtered)*100):.1f}%")

    with col3:
        transfer_count = len(df_filtered[df_filtered['payment_type'] == 'TRANSFER'])
        st.metric("Transfer Trx", transfer_count, f"{(transfer_count/len(df_filtered)*100):.1f}%")

    with col4:
        outstanding = df_filtered[df_filtered['is_paid'] == False]['total_revenue'].sum()
        st.metric("Outstanding", f"Rp {outstanding:,.0f}")

    # Payment Type Chart
    col1, col2 = st.columns(2)

    with col1:
        payment_type = df_filtered['payment_type'].value_counts()

        fig = px.pie(
            values=payment_type.values,
            names=payment_type.index,
            title='Payment Type Distribution',
            hole=0.4,
            color_discrete_map={'CASH': '#2ECC71', 'CREDIT': '#E74C3C', 'TRANSFER': '#3498DB'}
        )
        fig.update_traces(textinfo='percent+label+value')
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        payment_status = df_filtered.groupby(['payment_type', 'payment_status']).size().unstack(fill_value=0)

        fig = go.Figure()
        for status in payment_status.columns:
            fig.add_trace(go.Bar(
                name=status,
                x=payment_status.index,
                y=payment_status[status],
                text=payment_status[status],
                textposition='inside'
            ))

        fig.update_layout(
            title='Payment Type vs Status',
            barmode='stack',
            xaxis_title='Payment Type',
            yaxis_title='Count',
            template='plotly_white',
            height=350
        )

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Outstanding Analysis
    st.subheader("⚠️ Outstanding Payments")

    outstanding_df = df_filtered[df_filtered['is_paid'] == False].copy()

    if len(outstanding_df) > 0:
        outstanding_by_customer = outstanding_df.groupby('customer_name').agg({
            'total_revenue': 'sum',
            'bill_no': 'count',
            'customer_channel': 'first',
            'salesman_name': 'first'
        }).sort_values('total_revenue', ascending=False)

        st.dataframe(
            outstanding_by_customer.head(20),
            column_config={
                'customer_name': 'Customer',
                'total_revenue': st.column_config.NumberColumn('Outstanding (Rp)', format='Rp %,.0f'),
                'bill_no': '# Trx',
                'customer_channel': 'Channel',
                'salesman_name': 'Salesman'
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.success("✅ No outstanding payments!")

    st.markdown("---")

    # Collection by Salesman
    st.subheader("👤 Collection Responsibility by Salesman")

    collection = df_filtered.groupby('salesman_name').agg({
        'bill_no': 'count',
        'total_revenue': 'sum',
        'is_credit': 'sum',
        'is_paid': lambda x: (~(x.astype(bool))).sum()
    }).reset_index()
    collection.columns = ['Salesman', 'Total Trx', 'Revenue', 'Credit Trx', 'Outstanding Trx']
    collection['Outstanding Amount'] = df_filtered[df_filtered['is_paid'] == False].groupby('salesman_name')['total_revenue'].sum().reindex(collection['Salesman']).fillna(0).values

    collection = collection.sort_values('Revenue', ascending=False)

    st.dataframe(
        collection,
        column_config={
            'Salesman': st.column_config.TextColumn('Salesman'),
            'Total Trx': st.column_config.NumberColumn('Trx'),
            'Revenue': st.column_config.NumberColumn('Revenue (Rp)', format='Rp %,.0f'),
            'Credit Trx': st.column_config.NumberColumn('Credit #'),
            'Outstanding Trx': st.column_config.NumberColumn('Outstanding #'),
            'Outstanding Amount': st.column_config.NumberColumn('Outstanding (Rp)', format='Rp %,.0f')
        },
        hide_index=True,
        use_container_width=True
    )

# ── SALES PERFORMANCE PAGE ─────────────────────────────────────────────────
elif page == "📈 Sales Performance":
    st.title("📈 Sales Performance")

    # Sales Performance Table
    st.subheader("🏆 Sales Performance Ranking")

    sales_display = sales_perf.copy()
    sales_display['Profit Margin %'] = (sales_display['profit'] / sales_display['revenue'] * 100).round(1)

    st.dataframe(
        sales_display,
        column_config={
            'salesman_name': 'Salesman',
            'transactions': st.column_config.NumberColumn('Trx'),
            'outlets_visited': st.column_config.NumberColumn('Outlets'),
            'revenue': st.column_config.NumberColumn('Revenue (Rp)', format='Rp %,.0f'),
            'profit': st.column_config.NumberColumn('Profit (Rp)', format='Rp %,.0f'),
            'qty_sold': st.column_config.NumberColumn('Qty Sold'),
            'avg_margin': st.column_config.NumberColumn('Avg Margin %', format='%.1f%%'),
            'avg_revenue_per_trx': st.column_config.NumberColumn('Avg/Trx (Rp)', format='Rp %,.0f'),
            'Profit Margin %': st.column_config.NumberColumn('Profit Margin %', format='%.1f%%')
        },
        hide_index=True,
        use_container_width=True
    )

    # Performance Charts
    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            sales_display.sort_values('revenue'),
            x='revenue',
            y='salesman_name',
            orientation='h',
            title='Revenue by Salesman',
            color='revenue',
            color_continuous_scale='Blues'
        )
        fig.update_xaxes(title="Revenue (Rp)")
        fig.update_yaxes(title="")
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            sales_display.sort_values('Profit Margin %'),
            x='Profit Margin %',
            y='salesman_name',
            orientation='h',
            title='Profit Margin by Salesman (%)',
            color='Profit Margin %',
            color_continuous_scale='Greens'
        )
        fig.update_xaxes(title="Profit Margin (%)")
        fig.update_yaxes(title="")
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Revenue by Channel per Salesman
    st.subheader("📊 Revenue by Channel per Salesman")

    channel_sales = df_filtered.pivot_table(
        index='salesman_name',
        columns='customer_channel',
        values='total_revenue',
        aggfunc='sum',
        fill_value=0
    )

    # Keep only top channels
    top_channels = df_filtered['customer_channel'].value_counts().head(8).index.tolist()
    channel_sales = channel_sales[[c for c in top_channels if c in channel_sales.columns]]

    fig = go.Figure(data=go.Bar(name='Revenue', x=channel_sales.index, y=channel_sales.sum(axis=1)))
    for channel in channel_sales.columns:
        fig.add_trace(go.Bar(name=channel, x=channel_sales.index, y=channel_sales[channel]))

    fig.update_layout(
        title='Revenue by Channel per Salesman',
        barmode='stack',
        xaxis_title='Salesman',
        yaxis_title='Revenue (Rp)',
        template='plotly_white',
        height=400,
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)

# ── RECOMMENDATIONS PAGE ───────────────────────────────────────────────────
elif page == "💡 Recommendations":
    st.title("💡 Strategic Recommendations")

    # Critical Actions
    st.markdown("<div class='danger-box'>🔥 <strong>CRITICAL - Immediate Action (0-7 days)</strong></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### 1. Win-back Churned Outlets
        - **89 outlets haven't transacted in >14 days**
        - **Action**: Assign dedicated team to call/visit
        - **Target**: Recall 30% within 2 weeks
        - **Potential recovery**: Rp ~5M+
        """)

        st.markdown("""
        ### 2. Collect Outstanding Payments
        - **Outstanding**: Rp 29.9M (14.9% of revenue)
        - **Top debtor**: GASEBO MAGELANG (Rp 22.4M)
        - **Action**: Assign collector, offer payment plan
        - **Target**: Collect 50% within 2 weeks
        """)

    with col2:
        st.markdown("""
        ### 3. Resolve Pending Deliveries
        - **107 transactions pending delivery (23.3%)**
        - **Risk**: Customer dissatisfaction → churn
        - **Action**: Investigate root cause, expedite
        - **Target**: Clear backlog in 3 days
        """)

        st.markdown("""
        ### 4. Secure Key Account
        - **GASEBO MAGELANG**: 1 transaksi = Rp 22.4M
        - **Risk**: Single point of failure
        - **Action**: Negotiate contract, payment terms
        - **Target**: Lock in long-term agreement
        """)

    st.markdown("---")

    # Short-term Actions
    st.markdown("<div class='warning-box'>⚠️ <strong>IMPORTANT - Short-term (1-3 months)</strong></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        ### 5. Product Diversification
        - **Cup 120ML dominates 56.6% revenue** (1 bulk order)
        - **Risk**: Volatile, dependency risk
        - **Action**:
          - Promote Cup 240ML & Botol variants
          - Bundle deals for cross-selling
        """)

        st.markdown("""
        ### 6. Loyalty Program
        - **82 outlets with repeat orders**
        - **Action**:
          - Tiered discounts (2nd, 5th, 10th order)
          - Exclusive promos for repeat buyers
        """)

    with col2:
        st.markdown("""
        ### 7. Territory Optimization
        - **LATHIEF**: 60% of transactions (overloaded)
        - **Other salesmen**: Underutilized
        - **Action**:
          - Redistribute outlets
          - Assign specific territories
        """)

        st.markdown("""
        ### 8. Channel Expansion
        - **Low penetration**:
          - RUMAH_TANGGA, RESTORAN
        - **Action**:
          - Targeted acquisition campaigns
          - Referral incentives
        """)

    with col3:
        st.markdown("""
        ### 9. Delivery Optimization
        - **Peak days**: Saturday, Thursday
        - **Action**:
          - Schedule deliveries on peak days
          - Optimize routes per area
        """)

        st.markdown("""
        ### 10. Payment Terms
        - **24% transactions on credit**
        - **Action**:
          - Review credit policies
          - Push for prepayment/transfer
          - Implement early payment discount
        """)

    st.markdown("---")

    # Medium-term Initiatives
    st.markdown("<div class='success-box'>✅ <strong>STRATEGIC - Medium-term (3-6 months)</strong></div>", unsafe_allow_html=True)

    st.markdown("""
    ### 11. Build Real-time Dashboard
    - **Metrics to track**:
      - Daily revenue & profit
      - Churn rate alerts
      - Outstanding by age
      - Delivery success rate

    ### 12. Predictive Analytics
    - **Churn prediction model**
      - Identify at-risk outlets early
      - Automated retention campaigns
    - **Sales forecasting**
      - Per salesman, per area
      - Inventory optimization

    ### 13. Sales Enablement
    - **Mobile app for salesmen**:
      - Customer visit logging
      - Order taking
      - Payment tracking
    - **Performance coaching**:
      - Regular review cycles
      - Best practice sharing

    ### 14. Customer Acquisition
    - **Target**: Add 50 new outlets in 6 months
    - **Focus channels**: RUMAH_TANGGA, RESTORAN
    - **Incentives**: Referral bonuses
    """)

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #7f8c8d; padding: 2rem;'>
    <p><strong>Arbas Market Intelligence Dashboard</strong></p>
    <p>Sales & Distribution Analytics | Generated with Streamlit</p>
    <p style='font-size: 0.8rem;'>Data: Mar–Apr 2026 | Last Updated: 2026-05-03</p>
</div>
""", unsafe_allow_html=True)
