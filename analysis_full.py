"""
SALES & DISTRIBUTION ANALYTICS
Arbas Market Intelligence - Data Analysis
Generated: 2026-05-03
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')
import os

# ── Setup ──────────────────────────────────────────────────────────────────
DATA_PATH = "/Users/user/Documents/03 KERJA/PT Multimedia Solusi Prima/2026/APRIL/Arbas Market Intelligence - Data/Dashboardanlys/test_data/master_sales_analysis.csv"
OUTPUT_DIR = "/Users/user/Documents/03 KERJA/PT Multimedia Solusi Prima/2026/APRIL/Arbas Market Intelligence - Data/Dashboardanlys/test_data"

df = pd.read_csv(DATA_PATH)

# ── Feature Engineering ─────────────────────────────────────────────────────
df['transaction_date'] = pd.to_datetime(df['transaction_date'])
df['delivery_date'] = pd.to_datetime(df['delivery_date'])
df['day_name'] = df['transaction_date'].dt.day_name()
df['month'] = df['transaction_date'].dt.month
df['week'] = df['transaction_date'].dt.isocalendar().week.astype(int)
df['date_only'] = df['transaction_date'].dt.date

# Extract hour from delivery_date
df['delivery_hour'] = df['delivery_date'].dt.hour

# Province extraction
df['city_prov'] = df['customer_city_prov'].str.strip()
df['province'] = df['city_prov'].str.extract(r',\s*(.+)$')[0]

sns=None  # visualizations skipped (matplotlib not available)

print("✅ Data loaded & features engineered")
print(f"   Rows: {len(df)}, Date: {df['transaction_date'].min().date()} → {df['transaction_date'].max().date()}")
print(f"   Revenue: Rp {df['total_revenue'].sum():,.0f} | Profit: Rp {df['gross_profit'].sum():,.0f}")
print(f"   Customers: {df['customer_id'].nunique()} | Products: {df['product_id'].nunique()}")
print("="*80)
print("SECTION 1: OUTLET / CUSTOMER ANALYTICS")
print("="*80)

# ── 1a. Outlet Segmentation (RFM) ────────────────────────────────────────────
reference_date = df['transaction_date'].max() + pd.Timedelta(days=1)
print("\n📊 [1a] OUTLET SEGMENTATION (RFM)")
print("-"*60)

rfm = df.groupby('customer_id').agg({
    'transaction_date': lambda x: (reference_date - x.max()).days,
    'bill_no': 'count',
    'total_revenue': 'sum',
    'quantity': 'sum',
    'customer_name': 'first',
    'customer_channel': 'first',
    'customer_city_prov': 'first'
}).reset_index()
rfm.columns = ['customer_id','recency','frequency','monetary','total_qty','customer_name','channel','city_prov']

# RFM scoring (manual binning — robust for small data)
def rfm_score(series, ascending=True):
    """Assign 1-5 score, higher value = better behavior."""
    try:
        labels = list(range(1, 6))
        return pd.qcut(series.rank(method='first'), 5, labels=labels)
    except:
        n = len(series.unique())
        labels = list(range(1, min(n, 5)+1))
        return pd.cut(series.rank(method='first'), bins=min(n,5), labels=labels)

rfm['R_score'] = rfm_score(rfm['recency'], ascending=False)  # lower recency = better
rfm['F_score'] = rfm_score(rfm['frequency'], ascending=True)
rfm['M_score'] = rfm_score(rfm['monetary'], ascending=True)

rfm['RFM_score'] = rfm['R_score'].astype(int) + rfm['F_score'].astype(int) + rfm['M_score'].astype(int)

def segment_rfm(row):
    # RFM_score range: 3-15
    rfm_median = rfm['RFM_score'].median()
    mon_median = rfm['monetary'].median()
    if row['RFM_score'] >= rfm_median + 2:
        if row['monetary'] >= mon_median:
            return 'Champions'
        else:
            return 'Loyal Customers'
    elif row['R_score'] >= 4:
        return 'Potential Loyalists'
    elif row['R_score'] >= 3:
        return 'Promising'
    elif row['F_score'] >= 4:
        return 'At Risk'
    else:
        return 'Churned/Hibernating'

rfm['segment'] = rfm.apply(segment_rfm, axis=1)

print("\nRFM Segments Distribution:")
seg_counts = rfm['segment'].value_counts()
for seg, cnt in seg_counts.items():
    pct = cnt / len(rfm) * 100
    print(f"  {seg:25s}: {cnt:3d} ({pct:5.1f}%)")

# Segment summary
seg_summary = rfm.groupby('segment').agg({
    'customer_id':'count','monetary':'mean','frequency':'mean','recency':'mean'
}).round(1)
seg_summary.columns = ['num_outlets','avg_revenue','avg_freq','avg_recency']
seg_summary['pct_outlets'] = (seg_summary['num_outlets']/len(rfm)*100).round(1)
print("\n📋 Segment Summary:")
print(seg_summary.to_string())

# Save RFM results
rfm.to_csv(os.path.join(OUTPUT_DIR, 'rfm_segments.csv'), index=False)
print("\n✅ RFM segmentation saved to rfm_segments.csv")

# ── 1b. Churn Analysis ───────────────────────────────────────────────────────
print("\n\n📉 [1b] CHURN ANALYSIS")
print("-"*60)

CHURN_THRESHOLD = 14
last_date = df['transaction_date'].max()
churn_cutoff = last_date - pd.Timedelta(days=CHURN_THRESHOLD)

churned = rfm[rfm['recency'] > CHURN_THRESHOLD].copy()
active = rfm[rfm['recency'] <= CHURN_THRESHOLD].copy()

print(f"Churn Threshold : > {CHURN_THRESHOLD} days since last transaction")
print(f"Analysis Date   : {last_date.date()}")
print(f"Cutoff Date     : {churn_cutoff.date()}")
print(f"\n  Active Outlets  : {len(active):3d} ({len(active)/len(rfm)*100:.1f}%)")
print(f"  Churned Outlets : {len(churned):3d} ({len(churned)/len(rfm)*100:.1f}%)")

at_risk = rfm[(rfm['recency'] <= CHURN_THRESHOLD) & (rfm['recency'] > 7)].copy()
print(f"  At-Risk (>7d, ≤14d): {len(at_risk):3d} ({len(at_risk)/len(rfm)*100:.1f}%)")

churned_sorted = churned.sort_values('monetary', ascending=False)
print("\nTop 10 Churned Outlets (by lost revenue potential):")
print(f"{'Outlet Name':<35} {'Channel':<20} {'Days Inactive':>13} {'Revenue (Rp)':>14}")
print("-"*85)
for _, row in churned_sorted.head(10).iterrows():
    print(f"{row['customer_name']:<35} {row['channel']:<20} {row['recency']:>13} {row['monetary']:>14,.0f}")

churned.to_csv(os.path.join(OUTPUT_DIR, 'churned_outlets.csv'), index=False)
print("\n✅ Churn analysis saved to churned_outlets.csv")

# ── 1c. Repeat Order Analysis (Fokus – 1 bulan) ─────────────────────────────
print("\n\n🔁 [1c] REPEAT ORDER ANALYSIS")
print("-"*60)

one_month_ago = df['transaction_date'].max() - pd.Timedelta(days=30)
df_1m = df[df['transaction_date'] >= one_month_ago]
print(f"Period: {one_month_ago.date()} → {df['transaction_date'].max().date()} (last 30 days)")

repeat_df = df_1m.groupby('customer_id').agg(
    num_transactions=('bill_no', 'count'),
    total_revenue=('total_revenue', 'sum'),
    total_qty=('quantity', 'sum'),
    first_trx=('transaction_date', 'min'),
    last_trx=('transaction_date', 'max'),
    customer_name=('customer_name', 'first'),
    channel=('customer_channel', 'first')
).reset_index()

repeat_df = repeat_df[repeat_df['num_transactions'] > 1].sort_values('num_transactions', ascending=False)
repeat_df['unique_products'] = df_1m[df_1m['customer_id'].isin(repeat_df['customer_id'])].groupby('customer_id')['product_name'].nunique().reindex(repeat_df['customer_id']).values
repeat_df['num_orders'] = repeat_df['num_transactions']
repeat_df['repeat_interval_days'] = (repeat_df['last_trx'] - repeat_df['first_trx']).dt.days / (repeat_df['num_orders'] - 1)

print(f"\nOutlets with Repeat Order (last 30 days): {len(repeat_df)}")
print(f"\nTop 10 Repeat Customers:")
print(f"{'Outlet Name':<35} {'Channel':<18} {'#Trx':>4} {'Revenue':>12} {'Products':>8} {'Avg Interval':>12}")
print("-"*95)
for _, row in repeat_df.head(10).iterrows():
    interval = f"{row['repeat_interval_days']:.1f} days" if pd.notna(row['repeat_interval_days']) else "N/A"
    print(f"{row['customer_name']:<35} {row['channel']:<18} {row['num_orders']:>4} {row['total_revenue']:>12,.0f} {int(row['unique_products']):>8} {interval:>12}")

print("\n📋 Repeat Order by Channel:")
print(repeat_df.groupby('channel').agg({'customer_id':'count','num_orders':'mean','total_revenue':'sum'}).rename(columns={'customer_id':'num_outlets'}).sort_values('num_outlets', ascending=False).to_string())

repeat_df.to_csv(os.path.join(OUTPUT_DIR, 'repeat_order_customers.csv'), index=False)
print("\n✅ Repeat order analysis saved to repeat_order_customers.csv")

# ── 1d. Channel "Lainnya" Analysis ───────────────────────────────────────────
print("\n\n📂 [1d] CHANNEL 'LAINNYA' ANALYSIS")
print("-"*60)

lainnya = df[df['customer_channel'] == 'LAINNYA']
print(f"Total transaksi 'Lainnya': {len(lainnya)}")
print(f"Total outlets: {lainnya['customer_id'].nunique()}")
print(f"Total revenue: Rp {lainnya['total_revenue'].sum():,.0f}")

print("\n📍 Dominasi Wilayah (Lainnya):")
prov_lainnya = lainnya.groupby('city_prov').agg(
    num_transactions=('bill_no','count'),
    num_outlets=('customer_id','nunique'),
    revenue=('total_revenue','sum')
).sort_values('revenue', ascending=False)
print(prov_lainnya.to_string())

print("\n🛒 Top Products (Lainnya):")
prod_lainnya = lainnya.groupby('product_name').agg(
    num_transactions=('bill_no','count'),
    num_outlets=('customer_id','nunique'),
    revenue=('total_revenue','sum'),
    qty=('quantity','sum')
).sort_values('revenue', ascending=False)
print(prod_lainnya.to_string())

# ── 1e. Consumption Rate ─────────────────────────────────────────────────────
print("\n\n📦 [1e] CONSUMPTION RATE")
print("-"*60)

consumption = df_1m.groupby(['customer_id','product_name']).agg(
    total_qty=('quantity','sum'),
    num_transactions=('bill_no','count'),
    span_days=('transaction_date', lambda x: (x.max()-x.min()).days+1)
).reset_index()

consumption['daily_consumption'] = consumption['total_qty'] / consumption['span_days']
consumption['avg_days_per_purchase'] = consumption['span_days'] / consumption['num_transactions']

print("Average days between purchases by product:")
print(df_1m.groupby('product_name').apply(
    lambda x: x.groupby('customer_id').agg(
        span=('transaction_date', lambda v: (v.max()-v.min()).days+1),
        trx=('bill_no','count')
    ).assign(avg_interval=lambda r: r['span']/(r['trx']-1)).replace([np.inf,-np.inf],np.nan)
).groupby('product_name')['avg_interval'].mean().round(1).to_string())

print("\nEstimated consumption rate (units/month/customer):")
cons_summary = consumption.groupby('product_name').agg(
    avg_daily=('daily_consumption','mean'),
    avg_interval=('avg_days_per_purchase','mean')
).round(2)
print(cons_summary.to_string())

# ── 1f. Area Potential ───────────────────────────────────────────────────────
print("\n\n🗺️ [1f] AREA POTENTIAL")
print("-"*60)

area = df.groupby('city_prov').agg(
    num_outlets=('customer_id','nunique'),
    num_transactions=('bill_no','count'),
    revenue=('total_revenue','sum'),
    profit=('gross_profit','sum')
).reset_index()
area['avg_revenue_per_outlet'] = area['revenue'] / area['num_outlets']
area = area.sort_values('revenue', ascending=False)

print("Area Performance (sorted by revenue):")
print(f"{'Wilayah':<45} {'Outlets':>7} {'Revenue':>14} {'Avg/Outlet':>12} {'Profit':>14}")
print("-"*95)
for _, row in area.iterrows():
    print(f"{row['city_prov']:<45} {row['num_outlets']:>7} {row['revenue']:>14,.0f} {row['avg_revenue_per_outlet']:>12,.0f} {row['profit']:>14,.0f}")

# Identify potential areas (low activity but existing outlets)
area['revenue_per_trx'] = area['revenue']/area['num_transactions']
high_potential = area[area['avg_revenue_per_outlet'] > area['avg_revenue_per_outlet'].median()]
low_activity = area[area['num_transactions'] < area['num_transactions'].median()]

print("\n🔥 High Potential Areas (above median revenue/outlet):")
print(high_potential[['city_prov','num_outlets','revenue','avg_revenue_per_outlet']].to_string(index=False))

print("\n💡 Opportunity Areas (low transaction frequency):")
print(low_activity[['city_prov','num_outlets','num_transactions','revenue']].to_string(index=False))

print("\n" + "="*80)
print("SECTION 2: PRODUCT & MARKET ANALYTICS")
print("="*80)

# ── 2a. Product Hierarchy ─────────────────────────────────────────────────────
print("\n📦 [2a] PRODUCT HIERARCHY")
print("-"*60)

product_perf = df.groupby('product_name').agg(
    transactions=('bill_no','count'),
    outlets=('customer_id','nunique'),
    revenue=('total_revenue','sum'),
    profit=('gross_profit','sum'),
    quantity=('quantity','sum'),
    margin_avg=('margin_percent','mean')
).reset_index()
product_perf['revenue_pct'] = (product_perf['revenue']/product_perf['revenue'].sum()*100).round(1)
product_perf = product_perf.sort_values('revenue', ascending=False)

print("Per Product Performance:")
print(f"{'Product':<25} {'Trx':>5} {'Outlets':>7} {'Revenue':>12} {'Profit':>12} {'Qty':>8} {'Margin%':>8} {'Rev%':>6}")
print("-"*85)
for _, row in product_perf.iterrows():
    print(f"{row['product_name']:<25} {row['transactions']:>5} {row['outlets']:>7} {row['revenue']:>12,.0f} {row['profit']:>12,.0f} {row['quantity']:>8} {row['margin_avg']:>8.1f} {row['revenue_pct']:>6.1f}%")

category_perf = df.groupby('category_name').agg(
    transactions=('bill_no','count'),
    outlets=('customer_id','nunique'),
    revenue=('total_revenue','sum'),
    profit=('gross_profit','sum'),
    margin_avg=('margin_percent','mean')
).reset_index()
category_perf['revenue_pct'] = (category_perf['revenue']/category_perf['revenue'].sum()*100).round(1)
category_perf = category_perf.sort_values('revenue', ascending=False)

print("\nPer Category Performance:")
print(category_perf.to_string(index=False))

# ── 2b. Market Share (Wilayah) ───────────────────────────────────────────────
print("\n\n🗺️ [2b] MARKET SHARE (WILAYAH)")
print("-"*60)

ms_area = df.groupby('city_prov').agg(
    revenue=('total_revenue','sum'),
    quantity=('quantity','sum')
).reset_index()
ms_area['revenue_share'] = (ms_area['revenue']/ms_area['revenue'].sum()*100).round(2)
ms_area['qty_share'] = (ms_area['quantity']/ms_area['quantity'].sum()*100).round(2)
ms_area = ms_area.sort_values('revenue_share', ascending=False)

print("Market Share by Area:")
print(f"{'Wilayah':<45} {'Revenue Share':>13} {'Qty Share':>10}")
print("-"*70)
for _, row in ms_area.head(15).iterrows():
    print(f"{row['city_prov']:<45} {row['revenue_share']:>12.1f}% {row['qty_share']:>9.1f}%")

# ── 2c. Price Analysis ───────────────────────────────────────────────────────
print("\n\n💰 [2c] PRICE ANALYSIS")
print("-"*60)

price_analysis = df.groupby(['product_name','customer_channel']).agg(
    avg_price=('selling_price','mean'),
    total_qty=('quantity','sum'),
    num_transactions=('bill_no','count')
).reset_index()

print("Price vs Volume by Channel:")
pivot_price = df.pivot_table(index='product_name', columns='customer_channel', values='selling_price', aggfunc='mean').round(0)
print(pivot_price.to_string())

print("\n\n" + "="*80)
print("SECTION 3: DELIVERY & OPERATIONS")
print("="*80)

# ── 3a. Delivery Tracking ─────────────────────────────────────────────────────
print("\n🚚 [3a] DELIVERY TRACKING")
print("-"*60)

delivery_perf = df.groupby('delivery_status').agg(
    count=('bill_no','count'),
    revenue=('total_revenue','sum')
).reset_index()
delivery_perf['pct'] = (delivery_perf['count']/delivery_perf['count'].sum()*100).round(1)
print("Delivery Status Overview:")
print(delivery_perf.to_string(index=False))

print("\n📍 Delivery Lead Time per Area:")
dlvr_area = df.groupby('city_prov').agg(
    avg_lead_time=('delivery_lead_time_days','mean'),
    success_rate=('is_delivered','mean'),
    count=('bill_no','count')
).sort_values('avg_lead_time', ascending=False)
print(dlvr_area.head(10).to_string())

# ── 3b. Delivery Behavior ─────────────────────────────────────────────────────
print("\n\n⏰ [3b] DELIVERY BEHAVIOR")
print("-"*60)

delivered = df[df['is_delivered'] == True]
print(f"Delivered transactions: {len(delivered)} ({len(delivered)/len(df)*100:.1f}%)")

if 'delivery_hour' in df.columns:
    hour_dist = delivered['delivery_hour'].value_counts().sort_index()
    print("\nDelivery Hour Distribution:")
    print(hour_dist.to_string())

# ── 3c. Scheduling Insight ───────────────────────────────────────────────────
print("\n\n📅 [3c] SCHEDULING INSIGHT")
print("-"*60)

day_perf = df.groupby('day_name').agg(
    transactions=('bill_no','count'),
    revenue=('total_revenue','sum'),
    outlets=('customer_id','nunique')
).reset_index()
day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
day_perf['day_name'] = pd.Categorical(day_perf['day_name'], categories=day_order, ordered=True)
day_perf = day_perf.sort_values('day_name')

print("Daily Performance:")
print(day_perf.to_string(index=False))

best_day = day_perf.loc[day_perf['revenue'].idxmax()]
print(f"\n🔥 Best Day: {best_day['day_name']} | Revenue: Rp {best_day['revenue']:,.0f} | Trx: {best_day['transactions']}")

print("\n" + "="*80)
print("SECTION 4: PAYMENT & COLLECTION")
print("="*80)

# ── 4a. Payment Tracking ─────────────────────────────────────────────────────
print("\n💳 [4a] PAYMENT TRACKING")
print("-"*60)

payment_perf = df.groupby(['payment_type','payment_status']).agg(
    count=('bill_no','count'),
    revenue=('total_revenue','sum')
).reset_index()
payment_perf['pct'] = (payment_perf['count']/len(df)*100).round(1)

print("Payment Type x Status:")
print(payment_perf.to_string(index=False))

print("\n📍 Payment Status by Area:")
pay_area = df.pivot_table(index='city_prov', columns='payment_status', values='bill_no', aggfunc='count', fill_value=0)
pay_area['total'] = pay_area.sum(axis=1)
pay_area['pending_pct'] = (pay_area.get('PENDING',0)/pay_area['total']*100).round(1)
print(pay_area.sort_values('total', ascending=False).head(10).to_string())

# ── 4b. Credit Risk ──────────────────────────────────────────────────────────
print("\n\n⚠️ [4b] CREDIT RISK")
print("-"*60)

credit_trx = df[df['is_credit'] == True]
print(f"Credit Transactions: {len(credit_trx)} ({len(credit_trx)/len(df)*100:.1f}%)")
print(f"Credit Revenue: Rp {credit_trx['total_revenue'].sum():,.0f}")

outstanding = df[(df['is_credit'] == True) & (df['is_paid'] == False)]
print(f"\nOutstanding Payments: {len(outstanding)} transactions")
print(f"Outstanding Amount: Rp {outstanding['total_revenue'].sum():,.0f}")

outstanding_by_customer = outstanding.groupby('customer_name').agg(
    amount=('total_revenue','sum'),
    count=('bill_no','count'),
    channel=('customer_channel','first')
).sort_values('amount', ascending=False)
print("\nTop 10 Customers with Outstanding:")
print(outstanding_by_customer.head(10).to_string())

# ── 4c. Collection Responsibility ─────────────────────────────────────────────
print("\n\n👤 [4c] COLLECTION RESPONSIBILITY")
print("-"*60)

collection = df.groupby('salesman_name').agg(
    total_trx=('bill_no','count'),
    total_revenue=('total_revenue','sum'),
    credit_trx=('is_credit','sum'),
    outstanding_trx=('is_paid', lambda x: (~x).sum()),
    outstanding_amount=('is_paid', lambda x: df.loc[x.index[~x], 'total_revenue'].sum() if (~x).any() else 0)
).reset_index()

# Fix outstanding_amount calculation
for idx, row in collection.iterrows():
    sm = row['salesman_name']
    sm_df = df[df['salesman_name'] == sm]
    outstanding_amt = sm_df[sm_df['is_paid'] == False]['total_revenue'].sum()
    collection.loc[idx, 'outstanding_amount'] = outstanding_amt

collection = collection.sort_values('total_revenue', ascending=False)
print("Collection Performance by Salesman:")
print(f"{'Salesman':<30} {'Trx':>5} {'Revenue':>14} {'Credit#':>8} {'Outstanding#':>12} {'Outstanding(Rp)':>15}")
print("-"*85)
for _, row in collection.iterrows():
    print(f"{row['salesman_name']:<30} {row['total_trx']:>5} {row['total_revenue']:>14,.0f} {int(row['credit_trx']):>8} {int(row['outstanding_trx']):>12} {row['outstanding_amount']:>15,.0f}")

print("\n" + "="*80)
print("SECTION 5: SALES ACTIVITY & PERFORMANCE")
print("="*80)

# ── 5a. Sales Performance Metrics ───────────────────────────────────────────
print("\n📈 [5a] SALES PERFORMANCE METRICS")
print("-"*60)

sales_perf = df.groupby('salesman_name').agg(
    transactions=('bill_no','count'),
    outlets_visited=('customer_id','nunique'),
    revenue=('total_revenue','sum'),
    profit=('gross_profit','sum'),
    qty_sold=('quantity','sum'),
    avg_margin=('margin_percent','mean'),
    avg_revenue_per_trx=('total_revenue','mean')
).reset_index().sort_values('revenue', ascending=False)

print("Sales Performance Summary:")
print(f"{'Salesman':<30} {'Trx':>5} {'Outlets':>7} {'Revenue':>14} {'Profit':>12} {'Qty':>8} {'Avg Margin':>10} {'Rev/Trx':>10}")
print("-"*100)
for _, row in sales_perf.iterrows():
    print(f"{row['salesman_name']:<30} {row['transactions']:>5} {row['outlets_visited']:>7} {row['revenue']:>14,.0f} {row['profit']:>12,.0f} {row['qty_sold']:>8} {row['avg_margin']:>10.1f}% {row['avg_revenue_per_trx']:>10,.0f}")

total_rev = sales_perf['revenue'].sum()
print(f"\n{'TOTAL':<30} {sales_perf['transactions'].sum():>5} {'':<7} {total_rev:>14,.0f}")
sales_perf.to_csv(os.path.join(OUTPUT_DIR, 'sales_performance.csv'), index=False)

# ── 5b. Top & Under Performer ────────────────────────────────────────────────
print("\n\n🏆 [5b] TOP & UNDER PERFORMERS")
print("-"*60)

median_rev = sales_perf['revenue'].median()
top_sales = sales_perf[sales_perf['revenue'] >= median_rev * 1.5]
under_sales = sales_perf[sales_perf['revenue'] < median_rev * 0.5]

print(f"Revenue Median: Rp {median_rev:,.0f}")
print("\n🏆 TOP PERFORMERS (≥1.5x median):")
print(top_sales[['salesman_name','transactions','revenue','profit','avg_margin']].to_string(index=False))

print("\n📉 UNDER PERFORMERS (<0.5x median):")
print(under_sales[['salesman_name','transactions','revenue','profit','avg_margin']].to_string(index=False))

# ── 5c. Faktor yang Mempengaruhi Performa ──────────────────────────────────
print("\n\n🔍 [5c] FAKTOR YANG MEMPENGARUHI PERFORMA")
print("-"*60)

# Revenue by channel per salesman
print("Revenue by Channel per Salesman:")
chan_sales = df.pivot_table(index='salesman_name', columns='customer_channel', values='total_revenue', aggfunc='sum', fill_value=0)
top_chans = df['customer_channel'].value_counts().head(8).index.tolist()
chan_sales = chan_sales[[c for c in top_chans if c in chan_sales.columns]]
chan_sales['TOTAL'] = chan_sales.sum(axis=1)
print(chan_sales.sort_values('TOTAL', ascending=False).drop(columns=['TOTAL']).head(10).to_string())

# Revenue by area per salesman
print("\nRevenue by Area per Salesman:")
area_sales = df.pivot_table(index='salesman_name', columns='city_prov', values='total_revenue', aggfunc='sum', fill_value=0)
top_areas = area_sales.sum(axis=0).sort_values(ascending=False).head(8).index.tolist()
area_sales_top = area_sales[top_areas]
area_sales_top['TOTAL'] = area_sales_top.sum(axis=1)
print(area_sales_top.sort_values('TOTAL', ascending=False).drop(columns=['TOTAL']).to_string())

# Correlation: visits vs revenue
print("\n📊 Visits vs Revenue Correlation:")
visits_rev = df.groupby('salesman_name').agg(
    visits=('bill_no','count'),
    revenue=('total_revenue','sum')
)
corr = visits_rev['visits'].corr(visits_rev['revenue'])
print(f"Correlation coefficient: {corr:.3f}")

print("\n" + "="*80)
print("SECTION 6: SUMMARY INSIGHTS & RECOMMENDATIONS")
print("="*80)

# ── Generate all insights ─────────────────────────────────────────────────────
print("\n" + "="*80)
print("📌 STRATEGIC INSIGHTS FOR CEO")
print("="*80)

total_rev = df['total_revenue'].sum()
total_profit = df['gross_profit'].sum()
total_outlets = df['customer_id'].nunique()
churn_rate = len(churned)/len(rfm)*100
active_outlets_1m = df[df['transaction_date'] >= one_month_ago]['customer_id'].nunique()
top_product_rev = product_perf.iloc[0]['revenue']
top_product_name = product_perf.iloc[0]['product_name']
top_product_pct = product_perf.iloc[0]['revenue_pct']
top_salesman = sales_perf.iloc[0]['salesman_name']
top_sales_rev = sales_perf.iloc[0]['revenue']
cash_pct = len(df[df['payment_type']=='CASH'])/len(df)*100
outstanding_pct = len(outstanding)/len(df)*100
outstanding_amount = outstanding['total_revenue'].sum()

print(f"""
🎯 EXECUTIVE SUMMARY
{'─'*60}
• Total Revenue (Mar–Apr 2026) : Rp {total_rev:,.0f}
• Gross Profit                 : Rp {total_profit:,.0f} ({total_profit/total_rev*100:.1f}% margin)
• Total Transactions           : {len(df):,}
• Active Outlets               : {total_outlets:,}
• Products Sold               : {df['product_id'].nunique()}
• Period                       : {df['transaction_date'].min().date()} → {df['transaction_date'].max().date()}

🔑 KEY INSIGHTS
{'─'*60}

1. 📦 PRODUCT
   • Galon 19 Liter mendominasi {top_product_pct:.0f}% revenue
     → Risk: over-reliance on 1 product
   • Margin rata-rata {df['margin_percent'].mean():.1f}% — ada produk dengan margin negatif
     → Perlu review pricing untuk produk2 low-margin

2. 👥 CUSTOMER
   • Churn rate: {churn_rate:.1f}% ({len(churned)} outlets tidak transaksi >14 hari)
   • Top channel: TOKO, RESTORAN, LAINNYA
   • Repeat order customer: {len(repeat_df)} outlets (dalam 30 hari)
   • Segmentasi: {seg_counts.to_dict()}

3. 💰 PAYMENT & COLLECTION
   • Cash transactions: {cash_pct:.0f}% → sehat tapi perlu diversifikasi
   • Outstanding payments: Rp {outstanding_amount:,.0f} ({outstanding_pct:.1f}% of transactions)
   • Credit risk: {len(outstanding)} unpaid credit transactions

4. 🚚 DELIVERY
   • Delivery success rate: {len(delivered)/len(df)*100:.1f}%
   • Same-day delivery (lead time 0): {df['delivery_lead_time_days'].eq(0).sum()} transactions
   • On-Delivery: hanya {df['delivery_status'].eq('ON_DELIVERY').sum()} transaksi

5. 📈 SALES PERFORMANCE
   • Top salesman: {top_salesman} (Rp {top_sales_rev:,.0f})
   • Under performers perlu evaluasi: {', '.join(under_sales['salesman_name'].tolist())}
   • Visits vs Revenue correlation: {corr:.2f} — efektivitas kunjungan perlu diukur

6. 🗺️ AREA
   • High revenue area: {area.iloc[0]['city_prov']} (Rp {area.iloc[0]['revenue']:,.0f})
   • Opportunity areas: {', '.join(low_activity['city_prov'].head(3).tolist())}

💡 ACTIONABLE RECOMMENDATIONS
{'─'*60}

IMMEDIATE (0–30 days):
  1. 🔥 Intensifikasi outreach ke {len(churned)} outlets churned
     — target: recall/win-back dalam 2 minggu
  2. 💰 Fokus penagihan outstanding Rp {outstanding_amount:,.0f}
     — assign collector per salesman
  3. 📦 Diversifikasi produk: edukasi pasar untuk Cup & Botol
     — Galon mendominasi {top_product_pct:.0f}% revenue, terlalu berisiko

SHORT-TERM (1–3 months):
  4. 👥 Program loyalty untuk Top 10 repeat order customers
     — diskon/komisi khusus untuk repeat buyer
  5. 📍 Ekpansi ke opportunity areas
     — tambah kunjungan sales ke wilayah low activity
  6. 🚚 Optimasi scheduling pengiriman
     — hari & jam optimal berdasarkan section 3c

MEDIUM-TERM (3–6 months):
  7. 📊 Bangun dashboard real-time monitoring
     — KPI: revenue, churn rate, outstanding, delivery rate
  8. 🔮 Predictive model untuk:
     — Churn prediction (who will stop buying)
     — Sales forecast per salesman per area
  9. 📋 Evaluasi salesman underperformer
     — coaching plan atau redistribusi wilayah
 10. 🏪 Strategi akuisisi outlet baru
     — fokus ke channel RUMAH_TANGGA & RESTORAN

""")

# Save summary
summary_data = {
    'metric': ['Total Revenue','Gross Profit','Total Transactions','Active Outlets','Churn Rate %',
               'Outstanding Amount','Credit Transactions','Delivery Success Rate','Top Product',
               'Top Salesman'],
    'value': [f"Rp {total_rev:,.0f}", f"Rp {total_profit:,.0f}", len(df), total_outlets,
              f"{churn_rate:.1f}%", f"Rp {outstanding_amount:,.0f}", len(credit_trx),
              f"{len(delivered)/len(df)*100:.1f}%", top_product_name, top_salesman]
}
summary_df = pd.DataFrame(summary_data)
summary_df.to_csv(os.path.join(OUTPUT_DIR, 'executive_summary.csv'), index=False)

print("="*80)
print("ANALYSIS COMPLETE — All outputs saved to output directory")
print("="*80)
print(f"\nFiles generated:")
print(f"  • rfm_segments.csv")
print(f"  • churned_outlets.csv")
print(f"  • repeat_order_customers.csv")
print(f"  • sales_performance.csv")
print(f"  • executive_summary.csv")