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
    return render_template('landing.html')

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

    return render_template('analytics.html', 
                           dates=json.dumps(chart_dates), 
                           revenues=json.dumps(chart_values),
                           top_names=json.dumps(top_names),
                           top_qtys=json.dumps(top_qtys),
                           current_period=period, 
                           chart_label=chart_label,
                           date_range_info=date_range_info)