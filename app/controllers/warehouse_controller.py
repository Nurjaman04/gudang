from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Product, Transaction, db
from datetime import datetime

warehouse_bp = Blueprint('warehouse', __name__, url_prefix='/warehouse')

# 1. Warehouse Dashboard
@warehouse_bp.route('/')
def index():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    # Counts
    pending_picks = Transaction.query.filter_by(transaction_type='OUT', fulfillment_status='pending').count()
    pending_packs = Transaction.query.filter_by(transaction_type='OUT', fulfillment_status='picked').count()
    
    return render_template('warehouse/dashboard.html', 
                          pending_picks=pending_picks,
                          pending_packs=pending_packs)

# 2. Picking List
@warehouse_bp.route('/picking')
def picking_list():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    # Tasks: OUT transactions that are still 'pending'
    # We join with Product to display location clearly
    tasks = Transaction.query.filter_by(
        transaction_type='OUT', 
        fulfillment_status='pending'
    ).order_by(Transaction.created_at.asc()).all()
    
    return render_template('warehouse/picking.html', tasks=tasks)

# 3. Packing List
@warehouse_bp.route('/packing')
def packing_list():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    tasks = Transaction.query.filter_by(
        transaction_type='OUT', 
        fulfillment_status='picked'
    ).order_by(Transaction.created_at.asc()).all()
    
    return render_template('warehouse/packing.html', tasks=tasks)

# 4. Action: Update Status
@warehouse_bp.route('/update_status/<int:trx_id>/<status>')
def update_status(trx_id, status):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    trx = Transaction.query.get_or_404(trx_id)
    trx.fulfillment_status = status
    db.session.commit()
    
    flash(f'Status diperbarui menjadi: {status.upper()}', 'success')
    
    if status == 'picked': return redirect(url_for('warehouse.picking_list'))
    if status == 'packed' or status == 'shipped': return redirect(url_for('warehouse.packing_list'))
    
    return redirect(url_for('warehouse.index'))

# 5. Inventory Locations
@warehouse_bp.route('/locations', methods=['GET', 'POST'])
def locations():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    if request.method == 'POST':
        p_id = request.form['product_id']
        location = request.form['rack_location']
        
        p = Product.query.get(p_id)
        if p:
            p.rack_location = location
            db.session.commit()
            flash(f'Lokasi rak {p.name} berhasil diubah ke {location}', 'success')
            
    products = Product.query.order_by(Product.rack_location).all()
    return render_template('warehouse/locations.html', products=products)

# 6. Item Tracking
@warehouse_bp.route('/tracking')
def tracking():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    query = request.args.get('q')
    history = []
    product = None
    
    if query:
        # Search by SKU or Name
        product = Product.query.filter(
            (Product.sku == query) | (Product.name.ilike(f'%{query}%'))
        ).first()
        
        if product:
            history = Transaction.query.filter_by(product_id=product.id).order_by(Transaction.created_at.desc()).all()
        else:
            flash('Produk tidak ditemukan.', 'warning')
    
    return render_template('warehouse/tracking.html', product=product, history=history)
