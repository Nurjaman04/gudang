from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from app.models import Product, Transaction
from app import db
from datetime import datetime
import threading

# Import fungsi dari file service yang baru saja kita perbaiki
try:
    from app.services.notification_service import kirim_email_low_stock, kirim_wa_low_stock
except ImportError:
    def kirim_email_low_stock(n, s): pass
    def kirim_wa_low_stock(n, s): pass

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')

@sales_bp.route('/web/form', methods=['GET'])
def sales_page():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    products = Product.query.filter(Product.stock_quantity > 0).all()
    return render_template('sales.html', products=products)

@sales_bp.route('/web/process', methods=['POST'])
def process_sales_web():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))

    try:
        p_id = request.form['product_id']
        qty = int(request.form['quantity'])
        cust = request.form['customer_name']
        ref = request.form['reference']

        product = Product.query.get_or_404(p_id)

        if product.stock_quantity < qty:
            flash(f'Stok Kurang! Sisa: {product.stock_quantity}', 'danger')
            return redirect(url_for('sales.sales_page'))

        product.stock_quantity -= qty
        total_price = product.price * qty

        sale = Transaction(
            product_id=product.id, transaction_type='OUT', quantity=qty,
            total_amount=total_price, created_at=datetime.utcnow(),
            supplier=cust, reference=ref
        )
        
        db.session.add(sale)
        db.session.commit()

        # Cek Notifikasi
        if product.stock_quantity <= product.min_stock_threshold:
            t1 = threading.Thread(target=kirim_email_low_stock, args=(product.name, product.stock_quantity))
            t2 = threading.Thread(target=kirim_wa_low_stock, args=(product.name, product.stock_quantity))
            t1.start()
            t2.start()

        return redirect(url_for('sales.print_receipt', transaction_id=sale.id))

    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('sales.sales_page'))

@sales_bp.route('/receipt/<int:transaction_id>')
def print_receipt(transaction_id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    t = Transaction.query.get_or_404(transaction_id)
    return render_template('receipt.html', t=t)