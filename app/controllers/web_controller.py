import flask
from flask import Blueprint, render_template, session, redirect, url_for, request, send_file
from app.models import Product, Transaction
from app import db
from sqlalchemy import func
from datetime import datetime, timedelta
import pandas as pd
import io
import json

web_bp = Blueprint('web', __name__)

# --- 1. HALAMAN DEPAN ---
@web_bp.route('/')
def index():
    # 1. Simulasi Data Penjualan Cabang (Multi-Branch) - Tetap ada
    branches_data = {
        'names': ['Jakarta Pusat', 'Surabaya Timur', 'Bandung Barat', 'Medan Kota', 'Semarang'],
        'sales': [45000000, 32000000, 28000000, 15000000, 21000000],
        'colors': ['#2c3e50', '#c5a059', '#27ae60', '#c0392b', '#7f8c8d']
    }

    # 2. Data Real: Top 5 Produk Terlaris (Persentase)
    top_products_query = db.session.query(
        Product.name, func.sum(Transaction.quantity)
    ).join(Transaction).filter(
        Transaction.transaction_type == 'OUT'
    ).group_by(Product.name).order_by(func.sum(Transaction.quantity).desc()).limit(5).all()

    top_names = [p[0] for p in top_products_query]
    top_qtys = [p[1] for p in top_products_query]

    # 3. Data Real: Grafik Pendapatan 7 Hari Terakhir
    today = datetime.now()
    seven_days_ago = today - timedelta(days=6)
    
    transactions = Transaction.query.filter(
        Transaction.transaction_type == 'OUT',
        Transaction.created_at >= seven_days_ago
    ).all()

    # Agregasi per hari
    if not transactions:
        chart_dates = []
        chart_values = []
    else:
        data = [{'created_at': t.created_at, 'total': t.total_amount} for t in transactions]
        df = pd.DataFrame(data)
        df['created_at'] = pd.to_datetime(df['created_at'])
        df.set_index('created_at', inplace=True)
        
        # Resample Harian
        grouped = df.resample('D')['total'].sum().fillna(0)
        chart_dates = grouped.index.strftime('%d %b').tolist()
        chart_values = grouped.values.tolist()
    
    
    return render_template('landing.html', 
                           branches=branches_data,
                           top_names=top_names,
                           top_qtys=top_qtys,
                           trend_dates=chart_dates,
                           trend_values=chart_values)

# --- 2. DASHBOARD (DATA HARI INI) ---
@web_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    today = datetime.now() # Ensure we have full datetime for timedelta 
    start_of_today = today.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Hitung Pendapatan HARI INI
    total_revenue = db.session.query(func.sum(Transaction.total_amount))\
        .filter(Transaction.transaction_type == 'OUT')\
        .filter(Transaction.created_at >= start_of_today)\
        .scalar() or 0
        
    # 2. Hitung Barang Terjual HARI INI
    total_sold = db.session.query(func.sum(Transaction.quantity))\
        .filter(Transaction.transaction_type == 'OUT')\
        .filter(Transaction.created_at >= start_of_today)\
        .scalar() or 0
    
    # 3. Transaksi Terakhir (Tetap tampilkan 5 terakhir biar update)
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(5).all()

    summary = {
        'total_revenue': total_revenue,
        'total_items_sold': total_sold,
        'average_order_value': (total_revenue / total_sold) if total_sold > 0 else 0
    }

    # 4. CHART DATA: SALES TREND (7 Days)
    seven_days_ago = start_of_today - timedelta(days=6)
    sales_transactions = Transaction.query.filter(
        Transaction.transaction_type == 'OUT',
        Transaction.created_at >= seven_days_ago
    ).all()

    sales_dates = []
    sales_values = []
    
    if sales_transactions:
        data = [{'created_at': t.created_at, 'total': t.total_amount} for t in sales_transactions]
        df = pd.DataFrame(data)
        df['created_at'] = pd.to_datetime(df['created_at'])
        df.set_index('created_at', inplace=True)
        
        # Resample Daily - using 'D'
        grouped = df.resample('D')['total'].sum().fillna(0)
        sales_dates = grouped.index.strftime('%d %b').tolist()
        sales_values = grouped.values.tolist()
    else:
        # Create empty last 7 days chart if no data
        for i in range(7):
            d = seven_days_ago + timedelta(days=i)
            sales_dates.append(d.strftime('%d %b'))
            sales_values.append(0)

    # 5. CHART DATA: STOCK DISTRIBUTION (ByCategory)
    stock_distribution = db.session.query(Product.category, func.sum(Product.stock_quantity))\
        .group_by(Product.category).all()
    
    stock_labels = [s[0] if s[0] else 'General' for s in stock_distribution]
    stock_values = [int(s[1]) for s in stock_distribution]

    return render_template('dashboard.html', 
                           summary=summary, 
                           recent_transactions=recent_transactions,
                           sales_dates=json.dumps(sales_dates),
                           sales_values=json.dumps(sales_values),
                           stock_labels=json.dumps(stock_labels),
                           stock_values=json.dumps(stock_values))

# --- 3. INVENTORY ---
@web_bp.route('/inventory')
def inventory():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    products = Product.query.all()
    return render_template('index.html', products=products)

# --- 3.1 EXPORT INVENTORY ---
@web_bp.route('/inventory/export')
def export_inventory():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    products = Product.query.all()
    
    data = []
    for p in products:
        # Calculate status
        status = 'Menipis' if p.stock_quantity <= p.min_stock_threshold else 'Aman'
        
        data.append({
            'Kode Master': p.sku,
            'Nama Produk': p.name,
            'Kategori': p.category,
            'Harga Beli (Modal)': p.cost,
            'Harga Beli (Modal)': p.cost,
            'Stok Saat Ini': p.stock_quantity,
            'Batas Minimum': p.min_stock_threshold,
            'Nilai Aset (Stok * Modal)': p.stock_quantity * p.cost,

            'Status': status
        })
    
    df = pd.DataFrame(data)
    
    # Generate Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data Stok')
        
        # Auto-adjust column width (Basic)
        worksheet = writer.sheets['Data Stok']
        for column in df:
            column_length = max(df[column].astype(str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            worksheet.column_dimensions[chr(65 + col_idx)].width = column_length + 2

    output.seek(0)
    
    filename = f"Inventory_Stok_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True)

# --- 4. PENERIMAAN ---
@web_bp.route('/receiving')
def receiving_page():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    products = Product.query.all()
    return render_template('receiving.html', products=products)

# --- 5. LAPORAN ---
@web_bp.route('/laporan-final')
def laporan_final(): 
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    today = datetime.today()
    if not start_date_str: start_date = today.replace(day=1)
    else: start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

    if not end_date_str: end_date = today
    else: end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    end_date_fixed = end_date.replace(hour=23, minute=59, second=59)

    query = Transaction.query.filter(Transaction.created_at.between(start_date, end_date_fixed))
    transactions = query.order_by(Transaction.created_at.desc()).all()

    total_income = 0
    items_out = 0
    items_in = 0

    sales_recap = {}
    for t in transactions:
        if t.transaction_type == 'OUT':
            total_income += t.total_amount
            items_out += t.quantity
            
            # Rekap per Produk
            p_name = t.product.name
            if p_name not in sales_recap:
                sales_recap[p_name] = {'qty': 0, 'total': 0}
            sales_recap[p_name]['qty'] += t.quantity
            sales_recap[p_name]['total'] += t.total_amount
            
        elif t.transaction_type == 'TRANSFER_OUT':
            items_out += t.quantity
        elif t.transaction_type in ['IN', 'TRANSFER_IN']:
            items_in += t.quantity
            
    # Convert dict to sorted list
    sales_summary = [{'name': k, 'qty': v['qty'], 'total': v['total']} for k, v in sales_recap.items()]
    sales_summary.sort(key=lambda x: x['total'], reverse=True)

    return render_template('laporan_final.html', 
                           transactions=transactions,
                           total_income=total_income,
                           items_out=items_out,
                           items_in=items_in,
                           # sales_summary=sales_summary, # Removed from here as requested
                           start_date=start_date.strftime('%Y-%m-%d'),
                           end_date=end_date.strftime('%Y-%m-%d'))

# --- 5.1 REKAP PENJUALAN (FITUR BARU) ---
@web_bp.route('/laporan-rekap')
def laporan_rekap():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    today = datetime.today()
    if not start_date_str: start_date = today.replace(day=1)
    else: start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

    if not end_date_str: end_date = today
    else: end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    end_date_fixed = end_date.replace(hour=23, minute=59, second=59)

    # Get OUT transactions only
    transactions = Transaction.query.filter(
        Transaction.transaction_type == 'OUT',
        Transaction.created_at.between(start_date, end_date_fixed)
    ).all()

    sales_recap = {}
    for t in transactions:
        p_name = t.product.name
        if p_name not in sales_recap:
            sales_recap[p_name] = {'qty': 0, 'total': 0}
        sales_recap[p_name]['qty'] += t.quantity
        sales_recap[p_name]['total'] += t.total_amount
            
    sales_summary = [{'name': k, 'qty': v['qty'], 'total': v['total']} for k, v in sales_recap.items()]
    sales_summary.sort(key=lambda x: x['total'], reverse=True)

    return render_template('laporan_rekap.html',
                           sales_summary=sales_summary,
                           start_date=start_date.strftime('%Y-%m-%d'),
                           end_date=end_date.strftime('%Y-%m-%d'))

# --- 5.2 EXPORT REKAP EXCEL ---
@web_bp.route('/laporan-rekap/export')
def export_rekap_excel():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    today = datetime.today()
    if not start_date_str: start_date = today.replace(day=1)
    else: start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

    if not end_date_str: end_date = today
    else: end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    end_date_fixed = end_date.replace(hour=23, minute=59, second=59)

    # Get OUT transactions only
    transactions = Transaction.query.filter(
        Transaction.transaction_type == 'OUT',
        Transaction.created_at.between(start_date, end_date_fixed)
    ).all()

    sales_recap = {}
    for t in transactions:
        p_name = t.product.name
        if p_name not in sales_recap:
            sales_recap[p_name] = {'qty': 0, 'total': 0}
        sales_recap[p_name]['qty'] += t.quantity
        sales_recap[p_name]['total'] += t.total_amount
            
    sales_summary = [{'Nama Produk': k, 'Total Qty': v['qty'], 'Total Pendapatan': v['total']} for k, v in sales_recap.items()]
    sales_summary.sort(key=lambda x: x['Total Pendapatan'], reverse=True)

    df = pd.DataFrame(sales_summary)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Rekap Penjualan')
        
        # Auto-adjust column width
        worksheet = writer.sheets['Rekap Penjualan']
        for column in df:
            column_length = max(df[column].astype(str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            worksheet.column_dimensions[chr(65 + col_idx)].width = column_length + 2

    output.seek(0)
    
    filename = f"Rekap_Penjualan_{start_date.strftime('%d%m')}-{end_date.strftime('%d%m')}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True)

# --- 6. EXPORT EXCEL ---
@web_bp.route('/export-excel')
def export_excel():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    today = datetime.today()
    if not start_date_str: start_date = today.replace(day=1)
    else: start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

    if not end_date_str: end_date = today
    else: end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    end_date_fixed = end_date.replace(hour=23, minute=59, second=59)

    query = Transaction.query.filter(Transaction.created_at.between(start_date, end_date_fixed))
    transactions = query.order_by(Transaction.created_at.desc()).all()

    data_excel = []
    for t in transactions:
        # Tentukan Tipe Transaksi Text
        if t.transaction_type == 'IN':
            tipe_txt = 'BARANG MASUK'
        elif t.transaction_type == 'OUT':
            tipe_txt = 'PENJUALAN'
        elif t.transaction_type == 'TRANSFER_IN':
            tipe_txt = 'TRANSFER MASUK (DARI CABANG)'
        elif t.transaction_type == 'TRANSFER_OUT':
            tipe_txt = 'TRANSFER KELUAR (KE CABANG)'
        elif t.transaction_type == 'OPNAME':
            tipe_txt = 'STOK OPNAME (PENYESUAIAN)'
        else:
            tipe_txt = t.transaction_type

        data_excel.append({
            'Tanggal': t.created_at.strftime('%Y-%m-%d %H:%M'),
            'No. Referensi': t.reference,
            'Nama Barang': t.product.name,
            'Tipe Transaksi': tipe_txt,
            'Jumlah (Qty)': t.quantity,
            'Total Rupiah': t.total_amount if t.transaction_type == 'OUT' else 0,
            'Keterangan': t.supplier or t.branch_name or '-'
        })

    df = pd.DataFrame(data_excel)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Laporan Gudang')
    output.seek(0)
    
    filename = f"Laporan_{start_date.strftime('%d%m')}-{end_date.strftime('%d%m')}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True)

# --- 7. ANALITIK (DENGAN TANGGAL & PERBAIKAN IMPORT) ---
# --- 7. ADVANCED ANALYTICS ---
@web_bp.route('/analytics')
def analytics():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))

    period = request.args.get('period', 'monthly')
    now = datetime.now()
    
    # --- A. DATE FILTERING ---
    if period == 'daily':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        prev_start_date = start_date - timedelta(days=1) # Comparison
        group_freq = 'h'
        date_format = '%H:%M' 
        chart_label = 'Penjualan Hari Ini'
    elif period == 'weekly':
        start_date = now - timedelta(days=7)
        prev_start_date = start_date - timedelta(days=7)
        group_freq = 'D'
        date_format = '%A'
        chart_label = 'Tren 7 Hari Terakhir'
    elif period == 'yearly':
        start_date = now - timedelta(days=365)
        prev_start_date = start_date - timedelta(days=365)
        group_freq = 'ME'
        date_format = '%b %Y'
        chart_label = 'Tren 12 Bulan Terakhir'
    else: # Default: Monthly (30 Days)
        start_date = now - timedelta(days=30)
        prev_start_date = start_date - timedelta(days=30)
        group_freq = 'D'
        date_format = '%d %b'
        chart_label = 'Tren 30 Hari Terakhir'

    # --- B. DATA FETCHING ---
    transactions = Transaction.query.filter(
        Transaction.transaction_type == 'OUT',
        Transaction.created_at >= start_date
    ).all()
    
    # Convert to DataFrame
    if not transactions:
        df = pd.DataFrame(columns=['created_at', 'total_amount', 'quantity', 'product_name', 'customer', 'branch'])
    else:
        data = [{
            'created_at': t.created_at, 
            'total_amount': t.total_amount,
            'quantity': t.quantity,
            'product_name': t.product.name,
            'customer': t.supplier or 'Guest', # Using 'supplier' field as Customer Name
            'branch': t.branch_name or 'Main Store'
        } for t in transactions]
        df = pd.DataFrame(data)
        df['created_at'] = pd.to_datetime(df['created_at'])

    # --- 1. REVENUE & SALES PERFORMANCE (KPIs) ---
    total_revenue = df['total_amount'].sum() if not df.empty else 0
    total_sales_count = len(df)
    avg_order_value = total_revenue / total_sales_count if total_sales_count > 0 else 0
    
    # Comparison Logic (Growth Rate)
    prev_transactions = Transaction.query.filter(
        Transaction.transaction_type == 'OUT',
        Transaction.created_at >= prev_start_date,
        Transaction.created_at < start_date
    ).all()
    prev_revenue = sum([t.total_amount for t in prev_transactions])
    growth_rate = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0

    # --- 2. PRODUCT PERFORMANCE ---
    top_products = []
    worst_products = []
    if not df.empty:
        prod_perf = df.groupby('product_name').agg({'quantity': 'sum', 'total_amount': 'sum'}).reset_index()
        top_products = prod_perf.sort_values(by='total_amount', ascending=False).head(5).to_dict('records')
        worst_products = prod_perf.sort_values(by='total_amount', ascending=True).head(5).to_dict('records')

    # --- 3. CUSTOMER ANALYTICS ---
    # Top Customers by Revenue
    top_customers = []
    if not df.empty:
        cust_perf = df.groupby('customer').agg({'total_amount': 'sum', 'quantity': 'count'}).reset_index()
        top_customers = cust_perf.sort_values(by='total_amount', ascending=False).head(5).to_dict('records')

    # --- 4. SALES FUNNEL / CONVERSION (Repeat Rate) ---
    # We analyze if customers are returning (Retention)
    # Get all-time transactions for customer analysis
    all_out_trans = db.session.query(Transaction.supplier).filter(Transaction.transaction_type=='OUT').all()
    all_customers = [r[0] for r in all_out_trans if r[0]]
    if all_customers:
        from collections import Counter
        cust_counts = Counter(all_customers)
        one_time = sum(1 for k, v in cust_counts.items() if v == 1)
        repeat = sum(1 for k, v in cust_counts.items() if v > 1)
        total_unique = len(cust_counts)
        funnel_data = {
            'total_customers': total_unique,
            'one_time': one_time,
            'repeat': repeat,
            'retention_rate': round((repeat/total_unique)*100, 1) if total_unique > 0 else 0
        }
    else:
        funnel_data = {'total_customers': 0, 'one_time': 0, 'repeat': 0, 'retention_rate': 0}

    # --- 5. CHANNEL PERFORMANCE ---
    channel_data = {'labels': [], 'values': []}
    if not df.empty:
        chan_perf = df.groupby('branch')['total_amount'].sum()
        channel_data = {
            'labels': chan_perf.index.tolist(),
            'values': chan_perf.values.tolist()
        }

    # --- 6. TIME-BASED ANALYSIS (Main Chart) ---
    chart_dates = []
    chart_values = []
    
    if not df.empty:
        df_chart = df.set_index('created_at')
        try:
             # Handle 'ME' deprecation warning in newer pandas versions if necessary, using 'M' or logic
            if group_freq == 'ME': group_freq = 'M'
            grouped = df_chart.resample(group_freq)['total_amount'].sum().fillna(0)
            chart_dates = grouped.index.strftime(date_format).tolist()
            chart_values = grouped.values.tolist()
        except Exception:
            pass
            
    # --- 7. FORECASTING & PREDICTION (Simple Linear Regression) ---
    # We use the chart_values (historical) to predict next period
    forecast_dates = []
    forecast_values = []
    
    if len(chart_values) >= 5: # Need at least 5 data points
        # Pure Python Simple Linear Regression to avoid Numpy dependency
        n = len(chart_values)
        x_values = list(range(n))
        y_values = chart_values
        
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_xx = sum(x * x for x in x_values)
        
        denominator = (n * sum_xx - sum_x * sum_x)
        if denominator != 0:
            m = (n * sum_xy - sum_x * sum_y) / denominator
            b = (sum_y - m * sum_x) / n
            
            # Predict next 5 periods
            last_x = x_values[-1]
            for i in range(1, 6):
                next_val = m * (last_x + i) + b
                forecast_values.append(max(0, next_val)) # No negative revenue
                forecast_dates.append(f"Est. {i}")
        else:
             # Fallback if calculation fails
             forecast_values = []
             forecast_dates = []

    return render_template('analytics.html',
                           current_period=period,
                           chart_label=chart_label,
                           date_range_info=f"{start_date.strftime('%d %b')} - {now.strftime('%d %b')}",
                           
                           # 1. KPIs
                           total_revenue=total_revenue,
                           total_transactions=total_sales_count,
                           avg_order_value=avg_order_value,
                           growth_rate=growth_rate,
                           
                           # 2. Products
                           top_products=top_products,
                           worst_products=worst_products,
                           
                           # 3. Customer
                           top_customers=top_customers,
                           
                           # 4. Funnel
                           funnel=funnel_data,
                           
                           # 5. Channel
                           channel_labels=json.dumps(channel_data['labels']),
                           channel_values=json.dumps(channel_data['values']),
                           
                           # 6 & 7. Trend & Forecast
                           dates=json.dumps(chart_dates),
                           revenues=json.dumps(chart_values),
                           forecast_dates=json.dumps(forecast_dates),
                           forecast_values=json.dumps(forecast_values)
                           )

# --- 8. EXPORT ANALYTICS ---
@web_bp.route('/analytics/export')
def export_analytics():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))

    period = request.args.get('period', 'monthly')
    now = datetime.now()
    
    # Same filter logic as analytics
    if period == 'daily':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'weekly':
        start_date = now - timedelta(days=7)
    elif period == 'yearly':
        start_date = now - timedelta(days=365)
    else: 
        start_date = now - timedelta(days=30)

    transactions = Transaction.query.filter(
        Transaction.transaction_type == 'OUT',
        Transaction.created_at >= start_date
    ).all()
    
    if not transactions:
        # Return empty excel
        df = pd.DataFrame(columns=['Tanggal', 'No. Referensi', 'Produk', 'Qty', 'Total', 'Customer'])
    else:
        data = [{
            'Tanggal': t.created_at.strftime('%Y-%m-%d %H:%M'),
            'No. Referensi': t.reference or '-',
            'Produk': t.product.name,
            'Qty': t.quantity,
            'Total': t.total_amount,
            'Customer': t.supplier or 'Guest',
            'Cabang': t.branch_name or 'Main Store'
        } for t in transactions]
        df = pd.DataFrame(data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Analytics Data')
        # Auto-adjust column width
        worksheet = writer.sheets['Analytics Data']
        for column in df:
            column_length = max(df[column].astype(str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            worksheet.column_dimensions[chr(65 + col_idx)].width = column_length + 2

    output.seek(0)
    filename = f"Analytics_{period}_{now.strftime('%Y%m%d')}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True)
