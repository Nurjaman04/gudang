from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Supplier, PurchaseOrder, PurchaseOrderItem, Product, PurchaseReturn, db, Transaction, PurchaseRequest, PurchaseRequestItem
from app.services.accounting_service import AccountingService
from datetime import datetime
import json

purchasing_bp = Blueprint('purchasing', __name__, url_prefix='/purchasing')

@purchasing_bp.route('/')
def index():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    # Simple Purchasing Dashboard
    pos = PurchaseOrder.query.order_by(PurchaseOrder.created_at.desc()).limit(10).all()
    pending_pos = PurchaseOrder.query.filter_by(status='Sent').count()
    return render_template('purchasing/index.html', pos=pos, pending_pos=pending_pos)

@purchasing_bp.route('/suppliers')
def supplier_list():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('purchasing/supplier_list.html', suppliers=suppliers)

@purchasing_bp.route('/suppliers/add', methods=['POST'])
def add_supplier():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    try:
        s = Supplier(
            name=request.form['name'],
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            contact_person=request.form.get('contact_person')
        )
        db.session.add(s)
        db.session.commit()
        flash('Supplier ditambahkan.', 'success')
    except Exception as e:
        flash(f'Gagal: {e}', 'danger')
        
    return redirect(url_for('purchasing.supplier_list'))

@purchasing_bp.route('/po/create', methods=['GET', 'POST'])
def create_po():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    if request.method == 'POST':
        try:
            supplier_id = request.form['supplier_id']
            date_str = request.form['date']
            items_json = request.form['items_json']
            
            po_count = PurchaseOrder.query.filter(PurchaseOrder.date == date_str).count() + 1
            po_number = f"PO-{datetime.now().strftime('%Y%m')}-{po_count:04d}"
            
            new_po = PurchaseOrder(
                po_number=po_number,
                supplier_id=supplier_id,
                date=datetime.strptime(date_str, '%Y-%m-%d').date(),
                status='Draft'
            )
            db.session.add(new_po)
            db.session.flush()
            
            items = json.loads(items_json)
            total = 0
            
            for item in items:
                qty = int(item['qty'])
                cost = float(item['cost'])
                subtotal = qty * cost
                
                poi = PurchaseOrderItem(
                    purchase_order_id=new_po.id,
                    product_id=int(item['product_id']),
                    quantity=qty,
                    unit_cost=cost,
                    subtotal=subtotal
                )
                db.session.add(poi)
                total += subtotal
                
            new_po.total_amount = total
            db.session.commit()
            
            flash(f'PO {po_number} berhasil dibuat.', 'success')
            return redirect(url_for('purchasing.view_po', id=new_po.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal: {e}', 'danger')
            
    suppliers = Supplier.query.order_by(Supplier.name).all()
    products = Product.query.order_by(Product.name).all()
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('purchasing/po_form.html', suppliers=suppliers, products=products, today=today)

@purchasing_bp.route('/po/<int:id>')
def view_po(id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    po = PurchaseOrder.query.get_or_404(id)
    return render_template('purchasing/po_view.html', po=po)

@purchasing_bp.route('/po/<int:id>/send', methods=['POST'])
def send_po(id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    po = PurchaseOrder.query.get_or_404(id)
    po.status = 'Sent'
    db.session.commit()
    flash('Status PO berubah menjadi Sent (Terkirim).', 'success')
    return redirect(url_for('purchasing.view_po', id=id))

@purchasing_bp.route('/po/<int:id>/receive', methods=['POST'])
def receive_po(id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    po = PurchaseOrder.query.get_or_404(id)
    if po.status == 'Received':
        flash('PO ini sudah diterima.', 'warning')
        return redirect(url_for('purchasing.view_po', id=id))

    try:
        from app.services.inventory_engine import SmartInventoryEngine
        
        # Full Receive Logic (Assume all items arrived)
        for item in po.items:
            # Skip if already fully received (though UI checks status, safe implementation)
            if item.received_qty >= item.quantity:
                continue
                
            qty_to_receive = item.quantity - item.received_qty
            
            # 1. Use Smart Engine for Stock & Batch
            SmartInventoryEngine.process_inbound(
                product_id=item.product_id,
                quantity=qty_to_receive,
                cost_price=item.unit_cost,
                expiry_date=None, # Future: Allow inputting expiry during PO Receive
                auto_commit=False
            )
            
            # Update Master Stock (Denormalization)
            product = item.product
            product.stock_quantity += qty_to_receive
            product.cost = item.unit_cost # Last Purchase Price
            
            item.received_qty = item.quantity
            
            # 2. Record Transaction
            trx = Transaction(
                product_id=product.id,
                transaction_type='IN',
                quantity=qty_to_receive,
                supplier='PO ' + po.po_number,
                reference='RCV-' + po.po_number,
                created_at=datetime.utcnow()
            )
            db.session.add(trx)
            
        # 3. Accounting Journal
        try:
             AccountingService.record_purchase(
                 reference=f"PO-{po.po_number}",
                 amount=po.total_amount,
                 supplier=po.supplier.name
             )
        except Exception as e:
             print(f"Accounting Hook Error: {e}")
             
        po.status = 'Received'
        db.session.commit()
        
        flash('Barang berhasil diterima! Stok & Akuntansi terupdate (Batch Created).', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal Menerima: {e}', 'danger')
        
    return redirect(url_for('purchasing.view_po', id=id))

# PR & Returns (Placeholders to satisfy requirement structure)
# --- PURCHASE REQUESTS (PR) ---

@purchasing_bp.route('/pr')
def pr_list():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    prs = PurchaseRequest.query.order_by(PurchaseRequest.created_at.desc()).all()
    return render_template('purchasing/pr_list.html', prs=prs)

@purchasing_bp.route('/pr/create', methods=['GET', 'POST'])
def create_pr():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    if request.method == 'POST':
        try:
            date_str = request.form['date']
            notes = request.form.get('notes')
            items_json = request.form['items_json']
            
            # Generate PR Number: PR-YYYYMM-XXXX
            count = PurchaseRequest.query.filter(func.strftime('%Y-%m', PurchaseRequest.date) == datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m')).count() + 1
            pr_number = f"PR-{datetime.now().strftime('%Y%m')}-{count:04d}"
            
            new_pr = PurchaseRequest(
                pr_number=pr_number,
                date=datetime.strptime(date_str, '%Y-%m-%d').date(),
                notes=notes,
                status='Pending',
                requested_by=session['user_id']
            )
            db.session.add(new_pr)
            db.session.flush()
            
            items = json.loads(items_json)
            for item in items:
                pri = PurchaseRequestItem(
                    purchase_request_id=new_pr.id,
                    product_id=int(item['product_id']),
                    quantity=int(item['qty'])
                )
                db.session.add(pri)
                
            db.session.commit()
            flash(f'Purchase Request {pr_number} berhasil dibuat.', 'success')
            return redirect(url_for('purchasing.pr_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal: {e}', 'danger')
            
    products = Product.query.order_by(Product.name).all()
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('purchasing/pr_form.html', products=products, today=today)

@purchasing_bp.route('/pr/<int:id>')
def view_pr(id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    pr = PurchaseRequest.query.get_or_404(id)
    return render_template('purchasing/pr_view.html', pr=pr)

@purchasing_bp.route('/pr/<int:id>/approve', methods=['POST'])
def approve_pr(id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    pr = PurchaseRequest.query.get_or_404(id)
    pr.status = 'Approved'
    db.session.commit()
    flash('PR disetujui. Silakan buat PO.', 'success')
    return redirect(url_for('purchasing.view_pr', id=id))

# --- RETURNS ---

@purchasing_bp.route('/returns')
def return_list():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    returns = PurchaseReturn.query.order_by(PurchaseReturn.created_at.desc()).all()
    return render_template('purchasing/return_list.html', returns=returns)

@purchasing_bp.route('/po/<int:id>/return', methods=['GET', 'POST'])
def create_return(id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    po = PurchaseOrder.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            reason = request.form['reason']
            
            # Return Number
            ret_count = PurchaseReturn.query.count() + 1
            ret_number = f"RET-{datetime.now().strftime('%Y%m')}-{ret_count:04d}"
            
            new_ret = PurchaseReturn(
                return_number=ret_number,
                purchase_order_id=po.id,
                date=datetime.now().date(),
                reason=reason,
                status='Pending'
            )
            db.session.add(new_ret)
            
            # Note: Detailed Item Return logic would go here (selecting which items to return)
            # For now, we assume simple return logging or full return context
            
            db.session.commit()
            flash(f'Retur {ret_number} berhasil dicatat.', 'success')
            return redirect(url_for('purchasing.return_list'))
            
        except Exception as e:
            flash(f'Gagal: {e}', 'danger')
            
    return render_template('purchasing/return_form.html', po=po)
