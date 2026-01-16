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
    
    # Ambil Waktu Hari Ini (Mulai jam 00:00:00)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Hitung Pendapatan HARI INI
    total_revenue = db.session.query(func.sum(Transaction.total_amount))\
        .filter(Transaction.transaction_type == 'OUT')\
        .filter(Transaction.created_at >= today)\
        .scalar() or 0
        
    # 2. Hitung Barang Terjual HARI INI
    total_sold = db.session.query(func.sum(Transaction.quantity))\
        .filter(Transaction.transaction_type == 'OUT')\
        .filter(Transaction.created_at >= today)\
        .scalar() or 0
    
    # 3. Transaksi Terakhir (Tetap tampilkan 5 terakhir biar update)
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(5).all()

    summary = {
        'total_revenue': total_revenue,
        'total_items_sold': total_sold,
        'average_order_value': (total_revenue / total_sold) if total_sold > 0 else 0
    }
    return render_template('dashboard.html', summary=summary, recent_transactions=recent_transactions)

# --- 3. INVENTORY ---
@web_bp.route('/inventory')
def inventory():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    products = Product.query.all()
    return render_template('index.html', products=products)

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

    for t in transactions:
        if t.transaction_type == 'OUT':
            total_income += t.total_amount
            items_out += t.quantity
        else:
            items_in += t.quantity

    return render_template('laporan_final.html', 
                           transactions=transactions,
                           total_income=total_income,
                           items_out=items_out,
                           items_in=items_in,
                           start_date=start_date.strftime('%Y-%m-%d'),
                           end_date=end_date.strftime('%Y-%m-%d'))

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
        data_excel.append({
            'Tanggal': t.created_at.strftime('%Y-%m-%d %H:%M'),
            'No. Referensi': t.reference,
            'Nama Barang': t.product.name,
            'Tipe Transaksi': 'BARANG MASUK' if t.transaction_type == 'IN' else 'PENJUALAN',
            'Jumlah (Qty)': t.quantity,
            'Total Rupiah': t.total_amount if t.transaction_type == 'OUT' else 0,
            'Keterangan': t.supplier or '-'
        })

    df = pd.DataFrame(data_excel)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Laporan Gudang')
    output.seek(0)
    
    filename = f"Laporan_{start_date.strftime('%d%m')}-{end_date.strftime('%d%m')}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True)

# --- 7. ANALITIK (DENGAN TANGGAL & PERBAIKAN IMPORT) ---
@web_bp.route('/analytics')
def analytics():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))

    period = request.args.get('period', 'weekly')
    now = datetime.now()
    
    # LOGIKA PENENTUAN TANGGAL
    if period == 'daily':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        group_freq = 'h'
        date_format = '%H:%M' 
        chart_label = 'Penjualan Per Jam'
        date_range_info = now.strftime('%d %b %Y') # Contoh: 14 Jan 2026
        
    elif period == 'monthly':
        start_date = now - timedelta(days=30)
        group_freq = 'D'
        date_format = '%d %b'
        chart_label = 'Tren 30 Hari Terakhir'
        date_range_info = f"{start_date.strftime('%d %b')} - {now.strftime('%d %b %Y')}"

    elif period == 'yearly':
        start_date = now - timedelta(days=365)
        group_freq = 'ME'
        date_format = '%b %Y'
        chart_label = 'Tren 12 Bulan Terakhir'
        date_range_info = f"{start_date.strftime('%b %Y')} - {now.strftime('%b %Y')}"

    else: # Weekly (Default)
        start_date = now - timedelta(days=6)
        group_freq = 'D'
        date_format = '%A'
        chart_label = 'Tren 7 Hari Terakhir'
        date_range_info = f"{start_date.strftime('%d %b')} - {now.strftime('%d %b %Y')}"

    # QUERY DATABASE
    transactions = Transaction.query.filter(
        Transaction.transaction_type == 'OUT',
        Transaction.created_at >= start_date
    ).all()

    # OLAH DATA KE GRAFIK
    if not transactions:
        chart_dates = []
        chart_values = []
    else:
        data = [{'created_at': t.created_at, 'total': t.total_amount} for t in transactions]
        df = pd.DataFrame(data)
        df['created_at'] = pd.to_datetime(df['created_at'])
        df.set_index('created_at', inplace=True)

        try:
            grouped = df.resample(group_freq)['total'].sum().fillna(0)
        except:
            if group_freq == 'ME': group_freq = 'M'
            grouped = df.resample(group_freq)['total'].sum().fillna(0)

        chart_dates = grouped.index.strftime(date_format).tolist()
        chart_values = grouped.values.tolist()

    # TOP PRODUK
    top_products_query = db.session.query(
        Product.name, func.sum(Transaction.quantity)
    ).join(Transaction).filter(
        Transaction.transaction_type == 'OUT'
    ).group_by(Product.name).order_by(func.sum(Transaction.quantity).desc()).limit(5).all()

    top_names = [p[0] for p in top_products_query]
    top_qtys = [p[1] for p in top_products_query]

    # --- ADVANCED ANALYTICS: ABC ANALYSIS & INVENTORY HEALTH ---
    
    # 1. ABC Analysis (80/15/5 Rule based on Revenue)
    # Ambil semua produk dan total revenue-nya
    product_revenue = db.session.query(
        Product.name, func.sum(Transaction.total_amount).label('revenue')
    ).join(Transaction).filter(
        Transaction.transaction_type == 'OUT'
    ).group_by(Product.name).order_by(func.sum(Transaction.total_amount).desc()).all()

    total_revenue_all = sum([p.revenue for p in product_revenue]) or 0
    cumulative_revenue = 0
    abc_data = {'A': 0, 'B': 0, 'C': 0}
    
    # Kategori ABC: A (akumulasi s.d 80%), B (s.d 95%), C (sisanya)
    for p in product_revenue:
        cumulative_revenue += p.revenue
        percentage = (cumulative_revenue / total_revenue_all) * 100
        if percentage <= 80:
            abc_data['A'] += 1
        elif percentage <= 95:
            abc_data['B'] += 1
        else:
            abc_data['C'] += 1

    # 2. Dead Stock (Barang tidak terjual > 30 hari)
    thirty_days_ago = now - timedelta(days=30)
    
    # Subquery: ID produk yang ada transaksi OUT dalam 30 hari terakhir
    active_product_ids = db.session.query(Transaction.product_id).filter(
        Transaction.transaction_type == 'OUT',
        Transaction.created_at >= thirty_days_ago
    ).distinct()
    
    # Produk yang TIDAK ada di list active_product_ids
    dead_stock_products = Product.query.filter(Product.id.notin_(active_product_ids)).all()
    dead_stock_count = len(dead_stock_products)

    # 3. Critical Low Stock (Stock < Min Threshold)
    low_stock_products = Product.query.filter(Product.stock_quantity <= Product.min_stock_threshold).all()
    low_stock_count = len(low_stock_products)
    
    # 4. Actionable Recommendations (Sample)
    recommendations = []
    if low_stock_count > 0:
        recommendations.append({
            'type': 'danger', 
            'msg': f'{low_stock_count} Produk berada di bawah stok minimum. Segera lakukan restock.'
        })
    if dead_stock_count > 0:
        recommendations.append({
            'type': 'warning', 
            'msg': f'{dead_stock_count} Produk termasuk Dead Stock (tidak laku >30 hari). Pertimbangkan diskon/obral.'
        })
    if not product_revenue and total_revenue_all == 0:
         recommendations.append({
            'type': 'info', 
            'msg': 'Belum ada data penjualan yang cukup untuk analisis ABC.'
        })

    return render_template('analytics.html', 
                           dates=json.dumps(chart_dates), 
                           revenues=json.dumps(chart_values),
                           top_names=json.dumps(top_names),
                           top_qtys=json.dumps(top_qtys),
                           current_period=period, 
                           chart_label=chart_label,
                           date_range_info=date_range_info,
                           abc_data=abc_data,
                           dead_stock_count=dead_stock_count,
                           low_stock_count=low_stock_count,
                           recommendations=recommendations)