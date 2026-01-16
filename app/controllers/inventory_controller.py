from flask import Blueprint, request, jsonify, redirect, url_for, flash, session
from app.models import Product, Transaction
from app import db

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')

# --- [BARU] Endpoint Khusus untuk Form Web ---
@inventory_bp.route('/add_web', methods=['POST'])
def add_product_web():
    # Cek login (Keamanan)
    if 'user_id' not in session:
        return redirect(url_for('auth.login_web'))

    try:
        # Ambil data dari form HTML
        sku = request.form['sku']
        name = request.form['name']
        price = float(request.form['price'])
        cost = float(request.form['cost'])
        stock = int(request.form['stock'])
        min_stock = int(request.form['min_stock'])
        
        # Cek apakah SKU sudah ada (Mencegah duplikat)
        existing_product = Product.query.filter_by(sku=sku).first()
        if existing_product:
            flash(f'Gagal! Kode Barang (SKU) "{sku}" sudah ada.', 'danger')
            return redirect(url_for('web.inventory'))

        # Buat object produk baru
        new_product = Product(
            sku=sku,
            name=name,
            price=price,
            cost=cost,
            stock_quantity=stock,
            min_stock_threshold=min_stock
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        flash('Berhasil menambahkan barang baru!', 'success')
        
    except Exception as e:
        # Jika ada error lain
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')
        
    return redirect(url_for('web.inventory'))

# ... (Biarkan kode API lama di bawahnya jika masih dibutuhkan untuk testing)
# ... (Import yang sudah ada biarkan saja)
from flask import Blueprint, request, jsonify, redirect, url_for, flash, session
from app.models import Product, Transaction
from app import db

# ... (Biarkan endpoint add_product_web yang tadi)

# --- [BARU] Endpoint untuk Restock Lewat Web ---
@inventory_bp.route('/restock_web', methods=['POST'])
def restock_product_web():
    if 'user_id' not in session:
        return redirect(url_for('auth.login_web'))

    try:
        p_id = request.form['product_id']
        amount = int(request.form['amount'])
        
        product = Product.query.get_or_404(p_id)
        
        # 1. Tambah Stok
        product.stock_quantity += amount
        
        # 2. Catat Transaksi Masuk (IN)
        transaction = Transaction(
            product_id=product.id,
            transaction_type='IN',
            quantity=amount,
            total_amount=0 # Biasanya restock dianggap biaya operasional, atau bisa diisi cost * amount
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        flash(f'Berhasil menambah stok {product.name} sebanyak {amount} pcs.', 'success')
        
    except Exception as e:
        flash(f'Gagal restock: {str(e)}', 'danger')
        
# Tambahkan di inventory_controller.py

@inventory_bp.route('/process_receiving', methods=['POST'])
def receiving_process():
    if 'user_id' not in session:
        return redirect(url_for('auth.login_web'))

    try:
        p_id = request.form['product_id']
        qty = int(request.form['quantity'])
        supplier = request.form['supplier']
        ref = request.form['reference']
        
        product = Product.query.get_or_404(p_id)
        
        # 1. Update Stok
        product.stock_quantity += qty
        
        # 2. Catat Transaksi Lengkap
        trx = Transaction(
            product_id=product.id,
            transaction_type='IN',
            quantity=qty,
            total_amount=0, 
            supplier=supplier,    # Simpan Supplier
            reference=ref         # Simpan No SJ
        )
        
        db.session.add(trx)
        db.session.commit()
        
        flash(f'Penerimaan {product.name} ({qty} pcs) dari {supplier} berhasil disimpan.', 'success')
        return redirect(url_for('web.inventory'))
        
    except Exception as e:
        flash(f'Gagal: {str(e)}', 'danger')
        return redirect(url_for('web.receiving_page'))
    return redirect(url_for('web.inventory'))