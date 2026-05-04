"""
BEHAVIOR ANALYSIS — OUTLET, CHANNEL & MARKET PATTERNS
Arbas Market Intelligence
Focus: Pola perilaku (tanpa revenue)
Generated: 2026-05-03
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

# ── Setup ────────────────────────────────────────────────────────────────────
DATA_PATH = "/Users/user/Documents/03 KERJA/PT Multimedia Solusi Prima/2026/APRIL/Arbas Market Intelligence - Data/Dashboardanlys/test_data/master_sales_analysis.csv"
OUTPUT_DIR = "/Users/user/Documents/03 KERJA/PT Multimedia Solusi Prima/2026/APRIL/Arbas Market Intelligence - Data/Dashboardanlys/test_data"

df = pd.read_csv(DATA_PATH)

# ── Feature Engineering ──────────────────────────────────────────────────────
df['transaction_date'] = pd.to_datetime(df['transaction_date'])
df['delivery_date'] = pd.to_datetime(df['delivery_date'])
df['day_name'] = df['transaction_date'].dt.day_name()
df['date_only'] = df['transaction_date'].dt.date
df['hour'] = df['transaction_date'].dt.hour
df['week'] = df['transaction_date'].dt.isocalendar().week.astype(int)
df['is_weekend'] = df['day_name'].isin(['Saturday', 'Sunday'])

df['city_prov'] = df['customer_city_prov'].str.strip()
df['province'] = df['city_prov'].str.extract(r',\s*(.+)$')[0]
df['city'] = df['city_prov'].str.extract(r'^([^,]+)')[0].str.strip()

reference_date = df['transaction_date'].max()
one_month_ago = reference_date - pd.Timedelta(days=30)
df_1m = df[df['transaction_date'] >= one_month_ago]

CHURN_THRESHOLD = 14
print("="*80)
print("BEHAVIOR ANALYSIS — OUTLET, CHANNEL & MARKET PATTERNS")
print("="*80)
print(f"Period: {df['transaction_date'].min().date()} → {df['transaction_date'].max().date()}")
print(f"Analysis Date: {reference_date.date()} | Churn Threshold: {CHURN_THRESHOLD} days")
print(f"Total Rows: {len(df)} | Outlets: {df['customer_id'].nunique()}")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION A: OUTLET BEHAVIOR
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("SECTION A: OUTLET BEHAVIOR")
print("="*80)

# ── A1. Outlet Transaction Frequency Distribution ─────────────────────────────
print("\n[A1] OUTLET TRANSACTION FREQUENCY DISTRIBUTION")
print("-"*60)

outlet_freq = df.groupby('customer_id').agg(
    num_transactions=('bill_no', 'count'),
    num_products=('product_name', 'nunique'),
    first_trx=('transaction_date', 'min'),
    last_trx=('transaction_date', 'max'),
    total_qty=('quantity', 'sum'),
    customer_name=('customer_name', 'first'),
    channel=('customer_channel', 'first'),
    city_prov=('city_prov', 'first'),
    salesman=('salesman_name', 'first')
).reset_index()

outlet_freq['active_days'] = (outlet_freq['last_trx'] - outlet_freq['first_trx']).dt.days + 1
outlet_freq['trx_per_day'] = (outlet_freq['num_transactions'] / outlet_freq['active_days']).round(3)
outlet_freq['days_since_last'] = (reference_date - outlet_freq['last_trx']).dt.days

freq_bins = [1, 2, 3, 5, 10, float('inf')]
freq_labels = ['1x', '2x', '3-4x', '5-9x', '10x+']
outlet_freq['freq_group'] = pd.cut(outlet_freq['num_transactions'], bins=freq_bins, labels=freq_labels)

freq_dist = outlet_freq['freq_group'].value_counts().reindex(freq_labels)
print("\nOutlet Frequency Distribution:")
total_outlets = len(outlet_freq)
for label in freq_labels:
    cnt = freq_dist.get(label, 0)
    print(f"  {label:8s}: {cnt:3d} outlets ({cnt/total_outlets*100:5.1f}%)")

print(f"\n  TOTAL     : {total_outlets:3d} outlets")

print("\n📋 Freq Group by Channel:")
freq_channel = pd.crosstab(outlet_freq['freq_group'], outlet_freq['channel'])
freq_channel_pct = pd.crosstab(outlet_freq['freq_group'], outlet_freq['channel'], normalize='columns') * 100
print("\n  Count:")
print(freq_channel.to_string())
print("\n  % per Channel:")
print(freq_channel_pct.round(1).to_string())

# ── A2. Outlet Purchase Behavior ──────────────────────────────────────────────
print("\n\n[A2] OUTLET PURCHASE BEHAVIOR")
print("-"*60)

print("\n📦 Products Purchased per Transaction:")
trx_products = df.groupby('bill_no')['product_name'].nunique()
print(f"  Min products/trx  : {trx_products.min()}")
print(f"  Max products/trx  : {trx_products.max()}")
print(f"  Mean products/trx : {trx_products.mean():.2f}")
print(f"  Median products/trx: {trx_products.median()}")

print("\n  Distribution of products per transaction:")
for n in sorted(trx_products.value_counts().index):
    cnt = trx_products.value_counts()[n]
    pct = cnt / len(trx_products) * 100
    print(f"    {n} product(s): {cnt} transactions ({pct:.1f}%)")

print("\n📦 Most Common Product Combinations (Multi-product transactions):")
multi_trx = df.groupby('bill_no').filter(lambda x: x['product_name'].nunique() > 1)
if len(multi_trx) > 0:
    combo = multi_trx.groupby('bill_no')['product_name'].apply(lambda x: ' + '.join(sorted(x.unique()))).value_counts().head(10)
    for combo_name, count in combo.items():
        print(f"  {combo_name:<45}: {count:3d}x")
else:
    print("  (Tidak ada multi-product transactions)")

print("\n📦 Quantity per Transaction:")
print(f"  Min qty/trx   : {df['quantity'].min()}")
print(f"  Max qty/trx   : {df['quantity'].max()}")
print(f"  Mean qty/trx  : {df['quantity'].mean():.1f}")
print(f"  Median qty/trx: {df['quantity'].median():.0f}")

qty_bins = [1, 3, 5, 10, 20, 50, float('inf')]
qty_labels = ['1-2', '3-4', '5-9', '10-19', '20-49', '50+']
df['qty_group'] = pd.cut(df['quantity'], bins=qty_bins, labels=qty_labels)
qty_dist = df['qty_group'].value_counts().reindex(qty_labels)
print("\n  Qty distribution:")
for label in qty_labels:
    cnt = qty_dist.get(label, 0)
    print(f"    {label:6s}: {cnt:3d} trx ({cnt/len(df)*100:5.1f}%)")

# ── A3. Recency & Activity Pattern ────────────────────────────────────────────
print("\n\n[A3] RECENCY & ACTIVITY PATTERN")
print("-"*60)

recency_order = ['0-3 days', '4-7 days', '8-14 days', '15-30 days', '30+ days']
recency_dist = pd.cut(
    outlet_freq['days_since_last'],
    bins=[0, 3, 7, 14, 30, float('inf')],
    labels=recency_order
).value_counts().reindex(recency_order, fill_value=0)

print("\n  Recency Distribution (days since last transaction):")
for label in recency_order:
    cnt = recency_dist.get(label, 0)
    print(f"    {label:12s}: {cnt:3d} outlets ({cnt/total_outlets*100:5.1f}%)")

churned = outlet_freq[outlet_freq['days_since_last'] > CHURN_THRESHOLD]
at_risk   = outlet_freq[(outlet_freq['days_since_last'] > 7) & (outlet_freq['days_since_last'] <= CHURN_THRESHOLD)]
active    = outlet_freq[outlet_freq['days_since_last'] <= 7]

print(f"\n  Active    (≤7 days)      : {len(active):3d} outlets ({len(active)/total_outlets*100:.1f}%)")
print(f"  At-Risk   (8-14 days)    : {len(at_risk):3d} outlets ({len(at_risk)/total_outlets*100:.1f}%)")
print(f"  Churned   (>14 days)     : {len(churned):3d} outlets ({len(churned)/total_outlets*100:.1f}%)")

# Average days between transactions per outlet
print("\n📅 Average Days Between Transactions per Outlet:")
customer_ids = []
intervals = []
for cust_id, grp in df.sort_values('transaction_date').groupby('customer_id'):
    dates = grp['transaction_date'].sort_values()
    diffs = dates.diff().dt.days.dropna()
    if len(diffs) > 0:
        customer_ids.append(cust_id)
        intervals.append(float(diffs.mean()))

avg_interval = pd.Series(intervals)
print(f"  Mean interval    : {avg_interval.mean():.1f} days")
print(f"  Median interval  : {avg_interval.median():.1f} days")

interval_bins = [0, 1, 3, 7, 14, float('inf')]
interval_labels = ['Daily', '2-3 days', '4-7 days', '8-14 days', '14+ days']
interval_dist = pd.cut(avg_interval, bins=interval_bins, labels=interval_labels).value_counts()
interval_order = ['Daily', '2-3 days', '4-7 days', '8-14 days', '14+ days']
interval_dist = interval_dist.reindex(interval_order)
print("\n  Purchase interval distribution:")
for label in interval_order:
    cnt = interval_dist.get(label, 0)
    print(f"    {label:12s}: {cnt:3d} outlets ({cnt/len(avg_interval)*100:.1f}%)")

# ── A4. Day & Hour Behavior ───────────────────────────────────────────────────
print("\n\n[A4] TRANSACTION DAY & HOUR BEHAVIOR")
print("-"*60)

day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
day_dist = df['day_name'].value_counts().reindex(day_order).fillna(0)
print("\n  Transaction Count by Day:")
for day in day_order:
    cnt = int(day_dist.get(day, 0))
    bar = '█' * (cnt // 2)
    print(f"    {day:10s}: {cnt:3d}  {bar}")

best_day = day_dist.idxmax()
print(f"\n  Peak day   : {best_day} ({int(day_dist.max())} transactions)")
print(f"  Lowest day : {day_dist.idxmin()} ({int(day_dist.min())} transactions)")

print("\n  Day Pattern by Channel:")
day_channel = pd.crosstab(df['day_name'], df['customer_channel'])
day_channel = day_channel.reindex(day_order)
# Only show top channels
top_chans = df['customer_channel'].value_counts().head(8).index.tolist()
day_channel_top = day_channel[[c for c in top_chans if c in day_channel.columns]]
print(day_channel_top.to_string())

print("\n  Hour Distribution (when transactions happen):")
hour_dist = df['hour'].value_counts().sort_index()
for hour in sorted(hour_dist.index):
    cnt = hour_dist[hour]
    bar = '█' * (cnt // 2)
    period = 'AM' if hour < 12 else 'PM'
    label = f"{hour:02d}:00 {period}"
    print(f"    {label:10s}: {cnt:3d}  {bar}")

# Peak hour analysis
peak_hour = hour_dist.idxmax()
peak_trx = hour_dist.max()
print(f"\n  Peak hour  : {peak_hour}:00 ({peak_trx} transactions)")

# Weekday vs Weekend
weekend_trx = len(df[df['is_weekend'] == True])
weekday_trx = len(df[df['is_weekend'] == False])
print(f"\n  Weekday vs Weekend:")
print(f"    Weekday : {weekday_trx} transactions ({weekday_trx/len(df)*100:.1f}%)")
print(f"    Weekend : {weekend_trx} transactions ({weekend_trx/len(df)*100:.1f}%)")

# ── A5. Product Preference per Outlet ─────────────────────────────────────────
print("\n\n[A5] PRODUCT PREFERENCE PER OUTLET")
print("-"*60)

outlet_product = df.groupby(['customer_id','product_name'])['quantity'].sum().reset_index()
top_product_per_outlet = outlet_product.loc[outlet_product.groupby('customer_id')['quantity'].idxmax()]

product_pref = top_product_per_outlet['product_name'].value_counts()
print("\n  Primary Product Preference (by outlet count):")
total = len(top_product_per_outlet)
for prod, cnt in product_pref.items():
    print(f"    {prod:<25s}: {cnt:3d} outlets ({cnt/total*100:.1f}%)")

print("\n  Product Switching (outlets buying >1 product):")
multi_prod_outlets = outlet_freq[outlet_freq['num_products'] > 1]
print(f"  {len(multi_prod_outlets)} outlets ({len(multi_prod_outlets)/total_outlets*100:.1f}%) buy more than 1 product type")

switch_df = df.groupby('customer_id')['product_name'].nunique()
switch_dist = switch_df.value_counts().sort_index()
print("\n  Number of products bought per outlet:")
for n_prod, cnt in switch_dist.items():
    print(f"    {n_prod} product(s): {cnt} outlets ({cnt/total_outlets*100:.1f}%)")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION B: CHANNEL BEHAVIOR
# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n" + "="*80)
print("SECTION B: CHANNEL BEHAVIOR")
print("="*80)

# ── B1. Channel Activity Overview ─────────────────────────────────────────────
print("\n[B1] CHANNEL ACTIVITY OVERVIEW")
print("-"*60)

chan_act = df.groupby('customer_channel').agg(
    num_transactions=('bill_no','count'),
    num_outlets=('customer_id','nunique'),
    total_qty=('quantity','sum'),
    avg_qty_per_trx=('quantity','mean'),
    num_products=('product_name','nunique'),
    num_salesmen=('salesman_name','nunique'),
    num_areas=('city_prov','nunique')
).reset_index()

chan_act['avg_trx_per_outlet'] = (chan_act['num_transactions'] / chan_act['num_outlets']).round(2)
chan_act['chan_pct_trx'] = (chan_act['num_transactions'] / len(df) * 100).round(1)
chan_act['chan_pct_outlets'] = (chan_act['num_outlets'] / df['customer_id'].nunique() * 100).round(1)
chan_act['chan_pct_qty'] = (chan_act['total_qty'] / df['quantity'].sum() * 100).round(1)
chan_act = chan_act.sort_values('num_transactions', ascending=False)

print(f"\n{'Channel':<22} {'Trx':>5} {'Outlets':>7} {'Qty':>6} {'Qty/Trx':>8} {'Products':>8} {'%Trx':>6} {'%Outlets':>9} {'Areas':>6}")
print("-"*82)
for _, row in chan_act.iterrows():
    print(f"{row['customer_channel']:<22} {row['num_transactions']:>5} {row['num_outlets']:>7} {row['total_qty']:>6} {row['avg_qty_per_trx']:>8.1f} {row['num_products']:>8} {row['chan_pct_trx']:>6.1f}% {row['chan_pct_outlets']:>8.1f}% {row['num_areas']:>6}")

# ── B2. Channel Activity Patterns ─────────────────────────────────────────────
print("\n\n[B2] CHANNEL TRANSACTION PATTERNS")
print("-"*60)

print("\n📅 Active Days per Channel:")
chan_day = pd.crosstab(df['customer_channel'], df['day_name'])
chan_day = chan_day.reindex(columns=day_order)
chan_day['Active Days'] = (chan_day > 0).sum(axis=1)
chan_day['Total'] = chan_day[day_order].sum(axis=1)
print(chan_day.to_string())

print("\n📦 Product Mix per Channel:")
chan_product = pd.crosstab(df['customer_channel'], df['product_name'])
top_prods = df['product_name'].value_counts().head(6).index.tolist()
chan_product_show = chan_product[[c for c in top_prods if c in chan_product.columns]]
print(chan_product_show.to_string())

print("\n🚚 Delivery Status per Channel:")
chan_delivery = pd.crosstab(df['customer_channel'], df['delivery_status'])
chan_delivery['Delivery Rate %'] = ((chan_delivery.get('DELIVERED', 0) / chan_delivery.sum(axis=1)) * 100).round(1)
print(chan_delivery.to_string())

# ── B3. Channel Concentration ──────────────────────────────────────────────────
print("\n\n[B3] CHANNEL CONCENTRATION")
print("-"*60)

print("\n  How many outlets per channel?")
chan_outlets = df.groupby('customer_channel')['customer_id'].nunique().sort_values(ascending=False)
print(f"  Total unique channels: {len(chan_outlets)}")
print(f"\n  Channel outlet distribution:")
for chan, cnt in chan_outlets.head(15).items():
    bar = '█' * (cnt // 2)
    print(f"    {chan:<22}: {cnt:3d} outlets  {bar}")

top5_chan_outlets = chan_outlets.head(5).sum()
other_outlets = chan_outlets[5:].sum()
print(f"\n  Top 5 channels cover: {top5_chan_outlets} outlets ({top5_chan_outlets/df['customer_id'].nunique()*100:.1f}%)")
print(f"  Remaining {len(chan_outlets)-5} channels cover: {other_outlets} outlets ({other_outlets/df['customer_id'].nunique()*100:.1f}%)")

# ── B4. Payment Behavior per Channel ──────────────────────────────────────────
print("\n\n[B4] PAYMENT BEHAVIOR PER CHANNEL")
print("-"*60)

chan_payment = pd.crosstab(df['customer_channel'], df['payment_type'])
chan_payment['Cash %'] = (chan_payment.get('CASH', 0) / chan_payment.sum(axis=1) * 100).round(1)
chan_payment['Credit %'] = (chan_payment.get('CREDIT', 0) / chan_payment.sum(axis=1) * 100).round(1)
chan_payment['Transfer %'] = (chan_payment.get('TRANSFER', 0) / chan_payment.sum(axis=1) * 100).round(1)

print("  Payment type by channel (%):")
show_cols = [c for c in ['CASH','CREDIT','TRANSFER','Cash %','Credit %','Transfer %'] if c in chan_payment.columns]
print(chan_payment[show_cols].to_string())

# Credit behavior by channel
credit_chan = df[df['is_credit'] == True].groupby('customer_channel').size()
print("\n  Credit usage (is_credit=True) by channel:")
for chan, cnt in credit_chan.sort_values(ascending=False).items():
    print(f"    {chan:<22}: {cnt:3d} transactions")

# ── B5. Channel Salesman Assignment ───────────────────────────────────────────
print("\n\n[B5] CHANNEL-SALESMAN ASSIGNMENT PATTERN")
print("-"*60)

chan_salesman = pd.crosstab(df['customer_channel'], df['salesman_name'])
top_salesmen = df['salesman_name'].value_counts().head(6).index.tolist()
chan_salesman_show = chan_salesman[[c for c in top_salesmen if c in chan_salesman.columns]]
print("  Channel ↔ Salesman transaction matrix (top 6 salesmen):")
print(chan_salesman_show.to_string())

print("\n  Primary salesman per channel:")
for chan in chan_salesman.index:
    row = chan_salesman.loc[chan]
    primary = row.idxmax()
    cnt = row.max()
    total = row.sum()
    print(f"    {chan:<22}: {primary:<30} ({cnt}/{total} trx = {cnt/total*100:.0f}%)")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION C: MARKET GEOGRAPHY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n" + "="*80)
print("SECTION C: MARKET GEOGRAPHY")
print("="*80)

# ── C1. Outlet Distribution by Area ───────────────────────────────────────────
print("\n[C1] OUTLET DISTRIBUTION BY AREA")
print("-"*60)

area_outlets = df.groupby('city_prov').agg(
    num_outlets=('customer_id','nunique'),
    num_transactions=('bill_no','count'),
    num_channels=('customer_channel','nunique'),
    num_products=('product_name','nunique'),
    total_qty=('quantity','sum'),
    num_salesmen=('salesman_name','nunique')
).reset_index().sort_values('num_outlets', ascending=False)

area_outlets['trx_per_outlet'] = (area_outlets['num_transactions'] / area_outlets['num_outlets']).round(2)
area_outlets['outlet_pct'] = (area_outlets['num_outlets'] / df['customer_id'].nunique() * 100).round(1)
area_outlets['trx_pct'] = (area_outlets['num_transactions'] / len(df) * 100).round(1)

print(f"\n{'Area':<48} {'Outlets':>7} {'%Out':>6} {'Trx':>5} {'%Trx':>5} {'Trx/OL':>7} {'Chans':>5} {'Sales':>5}")
print("-"*90)
for _, row in area_outlets.iterrows():
    print(f"{row['city_prov']:<48} {row['num_outlets']:>7} {row['outlet_pct']:>5.1f}% {row['num_transactions']:>5} {row['trx_pct']:>4.1f}% {row['trx_per_outlet']:>7.2f} {row['num_channels']:>5} {row['num_salesmen']:>5}")

print("\n  Summary:")
top5_area = area_outlets.head(5)['num_outlets'].sum()
print(f"  Top 5 areas: {top5_area} outlets ({top5_area/df['customer_id'].nunique()*100:.1f}% of all outlets)")
print(f"  Total unique areas: {len(area_outlets)}")

# ── C2. Channel Distribution per Area ─────────────────────────────────────────
print("\n\n[C2] CHANNEL DISTRIBUTION PER AREA")
print("-"*60)

area_channel = pd.crosstab(df['city_prov'], df['customer_channel'])
top5_areas = area_outlets.head(5)['city_prov'].tolist()
area_channel_top = area_channel.reindex(top5_areas).fillna(0).astype(int)
print("  Top 5 areas × Top 8 channels:")
top8_chans = df['customer_channel'].value_counts().head(8).index.tolist()
area_channel_show = area_channel_top[[c for c in top8_chans if c in area_channel_top.columns]]
print(area_channel_show.to_string())

print("\n  Dominant channel per area:")
for area in top5_areas:
    row = area_channel.loc[area]
    top_chan = row.idxmax()
    cnt = row.max()
    total = row.sum()
    print(f"    {area:<48}: {top_chan:<22} ({int(cnt)}/{int(total)} trx = {cnt/total*100:.0f}%)")

# ── C3. Salesman Coverage per Area ─────────────────────────────────────────────
print("\n\n[C3] SALESMAN COVERAGE PER AREA")
print("-"*60)

area_salesman = pd.crosstab(df['city_prov'], df['salesman_name'])
top6_salesmen = df['salesman_name'].value_counts().head(6).index.tolist()
area_salesman_top = area_salesman[[c for c in top6_salesmen if c in area_salesman.columns]].reindex(top5_areas).fillna(0).astype(int)
print("  Top 5 areas × Top 6 salesmen (transactions):")
print(area_salesman_top.to_string())

print("\n  Primary salesman per top area:")
for area in top5_areas:
    if area in area_salesman.index:
        row = area_salesman.loc[area]
        primary = row.idxmax()
        cnt = row.max()
        total = row.sum()
        print(f"    {area:<48}: {primary:<30} ({int(cnt)}/{int(total)} trx)")

# ── C4. Area Market Depth ──────────────────────────────────────────────────────
print("\n\n[C4] AREA MARKET DEPTH (Outlet Density)")
print("-"*60)

print("  How many channels per area?")
area_chan_count = area_outlets[['city_prov','num_outlets','num_channels','trx_per_outlet']].sort_values('num_outlets', ascending=False)
print(area_chan_count.to_string(index=False))

print("\n  Multi-channel areas (diversified markets):")
multi_chan_areas = area_outlets[area_outlets['num_channels'] >= 3].sort_values('num_outlets', ascending=False)
print(f"  {len(multi_chan_areas)} areas with 3+ channels")
for _, row in multi_chan_areas.iterrows():
    print(f"    {row['city_prov']:<48}: {row['num_outlets']} outlets, {row['num_channels']} channels")

single_chan_areas = area_outlets[area_outlets['num_channels'] == 1]
print(f"\n  Single-channel areas (specialized markets): {len(single_chan_areas)}")
for _, row in single_chan_areas.iterrows():
    chan = df[df['city_prov']==row['city_prov']]['customer_channel'].unique()[0]
    print(f"    {row['city_prov']:<48}: {row['num_outlets']} outlets, only [{chan}]")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION D: MARKET-SALES BEHAVIOR
# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n" + "="*80)
print("SECTION D: MARKET-SALES BEHAVIOR")
print("="*80)

# ── D1. Salesman Territory ─────────────────────────────────────────────────────
print("\n[D1] SALESMAN TERRITORY COVERAGE")
print("-"*60)

salesman_territory = df.groupby('salesman_name').agg(
    num_outlets=('customer_id','nunique'),
    num_transactions=('bill_no','count'),
    num_channels=('customer_channel','nunique'),
    num_areas=('city_prov','nunique'),
    num_products=('product_name','nunique'),
    total_qty=('quantity','sum')
).reset_index().sort_values('num_outlets', ascending=False)

salesman_territory['trx_per_outlet'] = (salesman_territory['num_transactions'] / salesman_territory['num_outlets']).round(2)
salesman_territory['outlet_pct'] = (salesman_territory['num_outlets'] / df['customer_id'].nunique() * 100).round(1)
salesman_territory['trx_pct'] = (salesman_territory['num_transactions'] / len(df) * 100).round(1)

print(f"\n{'Salesman':<30} {'Outlets':>7} {'%OL':>5} {'Trx':>5} {'%Trx':>5} {'Trx/OL':>7} {'Chans':>6} {'Areas':>6} {'Products':>9}")
print("-"*95)
for _, row in salesman_territory.iterrows():
    print(f"{row['salesman_name']:<30} {row['num_outlets']:>7} {row['outlet_pct']:>4.1f}% {row['num_transactions']:>5} {row['trx_pct']:>4.1f}% {row['trx_per_outlet']:>7.2f} {row['num_channels']:>6} {row['num_areas']:>6} {row['num_products']:>9}")

print("\n  Territory breadth (channels & areas per salesman):")
for _, row in salesman_territory.iterrows():
    print(f"    {row['salesman_name']:<30}: {row['num_channels']} channels, {row['num_areas']} areas")

# ── D2. Salesman-Channel Affinity ─────────────────────────────────────────────
print("\n\n[D2] SALESMAN-CHANNEL AFFINITY")
print("-"*60)

sm_chan = df.pivot_table(index='salesman_name', columns='customer_channel', values='bill_no', aggfunc='count', fill_value=0)
top_chans = df['customer_channel'].value_counts().head(10).index.tolist()
sm_chan_show = sm_chan[[c for c in top_chans if c in sm_chan.columns]].copy()
sm_chan_show['TOTAL'] = sm_chan_show.sum(axis=1)
sm_chan_show = sm_chan_show.sort_values('TOTAL', ascending=False).drop(columns=['TOTAL'])
print("  Transaction count matrix (Salesman × Channel):")
print(sm_chan_show.to_string())

print("\n  Primary channel per salesman:")
for sm in sm_chan_show.index:
    row = sm_chan.loc[sm]
    primary = row.idxmax()
    cnt = row.max()
    total = row.sum()
    print(f"    {sm:<30}: {primary:<22} ({int(cnt)}/{int(total)} trx = {cnt/total*100:.0f}%)")

# ── D3. Salesman Overlap (Territory Overlap) ───────────────────────────────────
print("\n\n[D3] TERRITORY OVERLAP (Outlet Sharing)")
print("-"*60)

outlet_sm = df.groupby('customer_id')['salesman_name'].nunique()
outlet_sm_dist = outlet_sm.value_counts().sort_index()
print("  How many salesmen cover each outlet?")
for n, cnt in outlet_sm_dist.items():
    print(f"    {n} salesman(s): {cnt} outlets ({cnt/total_outlets*100:.1f}%)")

print("\n  Outlets served by multiple salesmen (potential overlap/conflict):")
multi_sm_outlets = outlet_sm[outlet_sm > 1].index.tolist()
print(f"  {len(multi_sm_outlets)} outlets are visited by >1 salesman")

# ── D4. Daily Activity Pattern per Salesman ────────────────────────────────────
print("\n\n[D4] DAILY ACTIVITY PATTERN PER SALESMAN")
print("-"*60)

sm_day = df.pivot_table(index='salesman_name', columns='day_name', values='bill_no', aggfunc='count', fill_value=0)
sm_day = sm_day.reindex(columns=[c for c in day_order if c in sm_day.columns])
top_sms = salesman_territory.head(6)['salesman_name'].tolist()
sm_day_top = sm_day.reindex(top_sms)
print("  Daily transactions per salesman:")
print(sm_day_top.to_string())

print("\n  Most active day per salesman:")
for sm in top_sms:
    if sm in sm_day.index:
        row = sm_day.loc[sm]
        best_day = row.idxmax()
        best_cnt = row.max()
        total = row.sum()
        print(f"    {sm:<30}: {best_day:<10} ({int(best_cnt)}/{int(total)} trx = {best_cnt/total*100:.0f}%)")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION E: REPEAT ORDER PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n" + "="*80)
print("SECTION E: REPEAT ORDER PATTERNS")
print("="*80)

# ── E1. Repeat Rate by Segment ─────────────────────────────────────────────────
print("\n[E1] REPEAT RATE BY CHANNEL")
print("-"*60)

repeat_1m = df_1m.groupby('customer_id').agg(
    num_trx=('bill_no','count'),
    first_trx=('transaction_date','min'),
    last_trx=('transaction_date','max'),
    channel=('customer_channel','first'),
    city_prov=('city_prov','first')
).reset_index()

repeat_1m['is_repeat'] = repeat_1m['num_trx'] > 1
repeat_1m['num_repeat'] = repeat_1m['num_trx'] - 1
repeat_1m['span_days'] = (repeat_1m['last_trx'] - repeat_1m['first_trx']).dt.days + 1
repeat_1m['repeat_interval'] = repeat_1m['span_days'] / repeat_1m['num_repeat'].replace(0, 1)

print(f"  Period: {one_month_ago.date()} → {reference_date.date()}")
print(f"  Active outlets in period: {len(repeat_1m)}")

repeat_by_chan = repeat_1m.groupby('channel').agg(
    total_outlets=('customer_id','count'),
    repeat_outlets=('is_repeat','sum'),
    avg_trx=('num_trx','mean'),
    avg_repeat=('num_repeat','mean')
).reset_index()
repeat_by_chan['repeat_rate'] = (repeat_by_chan['repeat_outlets'] / repeat_by_chan['total_outlets'] * 100).round(1)
repeat_by_chan = repeat_by_chan.sort_values('repeat_rate', ascending=False)

print(f"\n{'Channel':<22} {'Total OL':>8} {'Repeat OL':>10} {'Repeat Rate':>12} {'Avg Trx':>8} {'Avg Repeat':>11}")
print("-"*75)
for _, row in repeat_by_chan.iterrows():
    bar = '█' * int(row['repeat_rate']/3)
    print(f"{row['channel']:<22} {int(row['total_outlets']):>8} {int(row['repeat_outlets']):>10} {row['repeat_rate']:>11.1f}% {row['avg_trx']:>8.1f} {row['avg_repeat']:>11.1f}  {bar}")

# ── E2. Repeat Rate by Area ─────────────────────────────────────────────────────
print("\n\n[E2] REPEAT RATE BY AREA")
print("-"*60)

repeat_by_area = repeat_1m.groupby('city_prov').agg(
    total_outlets=('customer_id','count'),
    repeat_outlets=('is_repeat','sum'),
    avg_trx=('num_trx','mean'),
    avg_repeat=('num_repeat','mean')
).reset_index()
repeat_by_area['repeat_rate'] = (repeat_by_area['repeat_outlets'] / repeat_by_area['total_outlets'] * 100).round(1)
repeat_by_area = repeat_by_area[repeat_by_area['total_outlets'] >= 2].sort_values('repeat_rate', ascending=False)

print(f"\n{'Area':<50} {'Total OL':>8} {'Repeat OL':>10} {'Repeat Rate':>12} {'Avg Trx':>8}")
print("-"*92)
for _, row in repeat_by_area.iterrows():
    bar = '█' * int(row['repeat_rate']/3)
    print(f"{row['city_prov']:<50} {int(row['total_outlets']):>8} {int(row['repeat_outlets']):>10} {row['repeat_rate']:>11.1f}% {row['avg_trx']:>8.1f}  {bar}")

# ── E3. Repeat Interval Pattern ─────────────────────────────────────────────────
print("\n\n[E3] REPEAT INTERVAL PATTERN")
print("-"*60)

repeat_customers_1m = repeat_1m[repeat_1m['is_repeat'] == True].copy()
print(f"  Repeat customers (last 30d): {len(repeat_customers_1m)}")

interval_bins2 = [0, 1, 3, 5, 7, 14, float('inf')]
interval_labels2 = ['Daily', '2-3 days', '4-5 days', '6-7 days', '8-14 days', '14+ days']
repeat_customers_1m['interval_group'] = pd.cut(
    repeat_customers_1m['repeat_interval'],
    bins=interval_bins2,
    labels=interval_labels2
)
interval_dist2 = repeat_customers_1m['interval_group'].value_counts().reindex(interval_labels2).fillna(0)
print("\n  Repeat interval distribution:")
for label in interval_labels2:
    cnt = int(interval_dist2.get(label, 0))
    pct = cnt/len(repeat_customers_1m)*100 if len(repeat_customers_1m) > 0 else 0
    bar = '█' * (cnt // 1)
    print(f"    {label:12s}: {cnt:3d} customers ({pct:5.1f}%)  {bar}")

print("\n  Repeat interval by channel:")
interval_by_chan = repeat_customers_1m.groupby('channel')['repeat_interval'].mean().sort_values()
print(interval_by_chan.round(1).to_string())

# ── E4. Repeat vs Non-Repeat ──────────────────────────────────────────────────
print("\n\n[E4] REPEAT vs NON-REPEAT OUTLETS COMPARISON")
print("-"*60)

repeat_1m['segment'] = repeat_1m['is_repeat'].map({True: 'Repeat (2x+)', False: 'One-time'})
comparison = repeat_1m.groupby('segment').agg(
    num_outlets=('customer_id','count'),
    num_transactions=('num_trx','sum'),
    span_days=('span_days','mean'),
    channels=('channel', lambda x: x.nunique()),
    areas=('city_prov', lambda x: x.nunique())
).reset_index()

comparison['trx_per_outlet'] = (comparison['num_transactions'] / comparison['num_outlets']).round(2)
print("  Comparison:")
print(comparison.to_string(index=False))

print("\n  Channels in repeat vs non-repeat:")
for seg in ['One-time', 'Repeat (2x+)']:
    subset = repeat_1m[repeat_1m['segment'] == seg]
    top5 = subset['channel'].value_counts().head(5)
    print(f"\n  [{seg}] — Top channels:")
    for chan, cnt in top5.items():
        print(f"    {chan:<22}: {cnt:3d} outlets ({cnt/len(subset)*100:.1f}%)")

# ── E5. Top Repeat Customers Detail ─────────────────────────────────────────────
print("\n\n[E5] TOP 20 REPEAT CUSTOMERS (Full Detail)")
print("-"*60)

repeat_detail = repeat_1m[repeat_1m['is_repeat'] == True].sort_values('num_trx', ascending=False)

print(f"{'#':>3} {'Outlet Name':<35} {'Channel':<20} {'Area':<40} {'Trx':>4} {'Span':>5} {'Interval':>9}")
print("-"*120)
for i, (_, row) in enumerate(repeat_detail.head(20).iterrows(), 1):
    interval = f"{row['repeat_interval']:.1f}d" if pd.notna(row['repeat_interval']) else "N/A"
    print(f"{i:>3} {row['customer_id'] if pd.notna(row['customer_id']) else 'N/A':<35} {str(row['channel']):<20} {str(row['city_prov']):<40} {int(row['num_trx']):>4} {int(row['span_days']):>5} {interval:>9}")

# ── E6. Recency Pattern of Repeat Customers ────────────────────────────────────
print("\n\n[E6] RECENCY OF REPEAT CUSTOMERS")
print("-"*60)

repeat_customers_1m['days_since_last'] = (reference_date - repeat_customers_1m['last_trx']).dt.days

recency_repeat = pd.cut(
    repeat_customers_1m['days_since_last'],
    bins=[0, 3, 7, 14, 30, float('inf')],
    labels=['0-3 days','4-7 days','8-14 days','15-30 days','30+ days']
).value_counts()
recency_order2 = ['0-3 days','4-7 days','8-14 days','15-30 days','30+ days']
recency_repeat = recency_repeat.reindex(recency_order2).fillna(0)

print("  Recency of repeat customers:")
for label in recency_order2:
    cnt = int(recency_repeat.get(label, 0))
    pct = cnt/len(repeat_customers_1m)*100 if len(repeat_customers_1m) > 0 else 0
    bar = '█' * (cnt // 1)
    print(f"    {label:12s}: {cnt:3d} ({pct:5.1f}%)  {bar}")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION F: CONSUMPTION & PRODUCT PATTERN
# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n" + "="*80)
print("SECTION F: PRODUCT CONSUMPTION PATTERNS")
print("="*80)

# ── F1. Product Transaction Frequency ──────────────────────────────────────────
print("\n[F1] PRODUCT TRANSACTION FREQUENCY")
print("-"*60)

prod_trx = df.groupby('product_name').agg(
    num_transactions=('bill_no','count'),
    num_outlets=('customer_id','nunique'),
    total_qty=('quantity','sum'),
    avg_qty_per_trx=('quantity','mean'),
    num_channels=('customer_channel','nunique'),
    num_areas=('city_prov','nunique'),
    avg_margin=('margin_percent','mean')
).reset_index().sort_values('num_transactions', ascending=False)

prod_trx['trx_pct'] = (prod_trx['num_transactions'] / len(df) * 100).round(1)
prod_trx['outlet_pct'] = (prod_trx['num_outlets'] / df['customer_id'].nunique() * 100).round(1)

print(f"\n{'Product':<25} {'Trx':>5} {'%Trx':>5} {'Outlets':>7} {'%OL':>5} {'Qty/Trx':>8} {'Chans':>5} {'Areas':>5}")
print("-"*75)
for _, row in prod_trx.iterrows():
    print(f"{row['product_name']:<25} {row['num_transactions']:>5} {row['trx_pct']:>4.1f}% {row['num_outlets']:>7} {row['outlet_pct']:>4.1f}% {row['avg_qty_per_trx']:>8.1f} {row['num_channels']:>5} {row['num_areas']:>5}")

# ── F2. Product-channel affinity ───────────────────────────────────────────────
print("\n\n[F2] PRODUCT-CHANNEL AFFINITY")
print("-"*60)

prod_chan = pd.crosstab(df['product_name'], df['customer_channel'])
print("  Transactions: Product × Channel")
print(prod_chan.to_string())

print("\n  Dominant channel per product:")
for prod in prod_chan.index:
    row = prod_chan.loc[prod]
    primary = row.idxmax()
    cnt = row.max()
    total = row.sum()
    print(f"    {prod:<25}: {primary:<22} ({int(cnt)}/{int(total)} trx = {cnt/total*100:.0f}%)")

# ── F3. Product-area affinity ──────────────────────────────────────────────────
print("\n\n[F3] PRODUCT-AREA AFFINITY")
print("-"*60)

prod_area = pd.crosstab(df['product_name'], df['city_prov'])
top5_prod = prod_trx.head(5)['product_name'].tolist()
prod_area_top = prod_area.reindex(top5_prod)[top5_areas]
print("  Top 5 products × Top 5 areas:")
print(prod_area_top.to_string())

print("\n  Dominant area per product:")
for prod in top5_prod:
    if prod in prod_area.index:
        row = prod_area.loc[prod]
        primary = row.idxmax()
        cnt = row.max()
        total = row.sum()
        print(f"    {prod:<25}: {primary:<48} ({int(cnt)}/{int(total)} trx)")

# ═══════════════════════════════════════════════════════════════════════════════
# FINAL: BEHAVIORAL INSIGHTS SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n" + "="*80)
print("SECTION G: BEHAVIORAL INSIGHTS SUMMARY")
print("="*80)

total_outlets = len(outlet_freq)
total_repeat = len(repeat_customers_1m)
repeat_rate = total_repeat / len(repeat_1m) * 100 if len(repeat_1m) > 0 else 0
one_time = len(repeat_1m) - total_repeat

print(f"""
🎯 BEHAVIORAL INSIGHTS SUMMARY
{'─'*60}

📍 OUTLET BEHAVIOR
{'─'*60}
• Total unique outlets   : {total_outlets}
• One-time buyers        : {one_time} ({one_time/len(repeat_1m)*100:.1f}% of active outlets)
• Repeat buyers (30d)    : {total_repeat} ({repeat_rate:.1f}% of active outlets)
• Top frequency group    : {outlet_freq['freq_group'].value_counts().idxmax()} ({outlet_freq['freq_group'].value_counts().max()} outlets)
• Avg purchase interval  : {avg_interval.mean():.1f} days | Median: {avg_interval.median():.1f} days
• Peak transaction day   : {best_day}
• Peak transaction hour  : {peak_hour}:00
• Outlets buying >1 product: {len(multi_prod_outlets)} ({len(multi_prod_outlets)/total_outlets*100:.1f}%)

📊 CHANNEL BEHAVIOR
{'─'*60}
• Total channels         : {df['customer_channel'].nunique()}
• Top channel by trx     : {df['customer_channel'].value_counts().idxmax()} ({df['customer_channel'].value_counts().max()} transactions)
• Top channel by outlets : {chan_outlets.idxmax()} ({chan_outlets.max()} outlets)
• Most cash-heavy channel: {chan_payment['Cash %'].idxmax()} ({chan_payment['Cash %'].max():.0f}% cash)
• Most credit-heavy channel: {chan_payment['Credit %'].idxmax()} ({chan_payment['Credit %'].max():.0f}% credit)
• Most repeat-prone channel: {repeat_by_chan.iloc[0]['channel']} ({repeat_by_chan.iloc[0]['repeat_rate']:.0f}% repeat rate)

🗺️ MARKET BEHAVIOR
{'─'*60}
• Total areas            : {len(area_outlets)}
• Top area by outlets    : {area_outlets.iloc[0]['city_prov']} ({area_outlets.iloc[0]['num_outlets']} outlets)
• Most diverse area      : {area_outlets.loc[area_outlets['num_channels'].idxmax(), 'city_prov']} ({int(area_outlets['num_channels'].max())} channels)
• Multi-channel areas    : {len(multi_chan_areas)}
• Single-channel areas   : {len(single_chan_areas)}

👤 SALESMAN BEHAVIOR
{'─'*60}
• Total salesmen         : {df['salesman_name'].nunique()}
• Top salesman           : {salesman_territory.iloc[0]['salesman_name']} ({int(salesman_territory.iloc[0]['num_outlets'])} outlets, {int(salesman_territory.iloc[0]['num_transactions'])} trx)
• Most active day (all)  : {best_day}
• Territory overlap      : {len(multi_sm_outlets)} outlets visited by >1 salesman
• Best channel coverage  : {sm_chan.sum(axis=0).idxmax()} ({sm_chan.sum(axis=0).max()} total trx)

🔁 REPEAT ORDER PATTERNS
{'─'*60}
• Repeat rate overall   : {repeat_rate:.1f}%
• Best repeat channel   : {repeat_by_chan.iloc[0]['channel']} ({repeat_by_chan.iloc[0]['repeat_rate']:.0f}% repeat)
• Worst repeat channel  : {repeat_by_chan.iloc[-1]['channel']} ({repeat_by_chan.iloc[-1]['repeat_rate']:.0f}% repeat)
• Best repeat area      : {repeat_by_area.iloc[0]['city_prov']} ({repeat_by_area.iloc[0]['repeat_rate']:.0f}% repeat)
• Most frequent interval : {repeat_customers_1m['repeat_interval'].median():.0f} days (median)

💡 KEY BEHAVIORAL RECOMMENDATIONS
{'─'*60}

1. 🔁 ONE-TIME BUYER CONVERSION
   {one_time} outlets ({one_time/len(repeat_1m)*100:.0f}%) hanya beli sekali
   → Target: follow-up dalam 3-7 hari setelah pembelian pertama
   → Channel TERBAIK untuk intercept: {repeat_by_chan.iloc[-1]['channel']} (paling sedikit repeat)

2. 📅 SCHEDULING OPTIMIZATION
   Peak day: {best_day} & Saturday
   → Alokasikan resource lebih di hari Kamis-Sabtu
   → {peak_hour}:00 adalah peak hour → jadwalkan kunjungan sebelum/sesudah jam ini

3. 🗺️ TERRITORY REBALANCING
   LATHIEF NUR S cover {int(salesman_territory.iloc[0]['outlet_pct'])}% outlets
   → Redistribusi outlet ke salesmen lain untuk coverage yang lebih merata
   → {len(multi_sm_outlets)} outlets overlap (visited by >1 salesman) → perlu clear boundary

4. 🏪 CHANNEL FOCUS
   Channel dengan repeat TERBAIK: {repeat_by_chan.iloc[0]['channel']} ({repeat_by_chan.iloc[0]['repeat_rate']:.0f}%)
   Channel dengan repeat TERBURUK: {repeat_by_chan.iloc[-1]['channel']} ({repeat_by_chan.iloc[-1]['repeat_rate']:.0f}%)
   → Fokus akuisisi di channel dengan high repeat potential

5. 🗺️ AREA EXPANSION
   Highest outlet density: {area_outlets.iloc[0]['city_prov']}
   → Area ini sudah matang → fokus ke kualitas (repeat) bukan kuantitas
   → Area CHURNED terbesar: {churned.sort_values('num_transactions', ascending=False).iloc[0]['city_prov'] if len(churned) > 0 else 'N/A'}
   → Perlu win-back campaign di area tersebut

6. 📦 PRODUCT BUNDLING
   {len(multi_prod_outlets)} outlets sudah beli >1 produk
   → Cross-sell opportunity: Galon + Cup/Botol
   → Product combo yang sering: lihat section A2
""")

# ── Save Outputs ──────────────────────────────────────────────────────────────
repeat_1m.to_csv(os.path.join(OUTPUT_DIR, 'behavior_repeat_patterns.csv'), index=False)
outlet_freq.to_csv(os.path.join(OUTPUT_DIR, 'behavior_outlet_frequency.csv'), index=False)
salesman_territory.to_csv(os.path.join(OUTPUT_DIR, 'behavior_salesman_territory.csv'), index=False)
repeat_by_chan.to_csv(os.path.join(OUTPUT_DIR, 'behavior_channel_repeat.csv'), index=False)
repeat_by_area.to_csv(os.path.join(OUTPUT_DIR, 'behavior_area_repeat.csv'), index=False)

print("\n" + "="*80)
print("BEHAVIOR ANALYSIS COMPLETE")
print("="*80)
print("\nFiles saved:")
print("  • behavior_repeat_patterns.csv   — Repeat order data (30d)")
print("  • behavior_outlet_frequency.csv  — Outlet frequency & behavior")
print("  • behavior_salesman_territory.csv — Salesman territory coverage")
print("  • behavior_channel_repeat.csv    — Channel repeat rates")
print("  • behavior_area_repeat.csv       — Area repeat rates")