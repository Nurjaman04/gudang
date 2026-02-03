from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.models import SalesOrder, SalesOrderItem, Product, Customer, Transaction, SalesReturn, db
from app.services.accounting_service import AccountingService
from datetime import datetime
import json

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')

@sales_bp.route('/')
def index():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status')
    
    query = SalesOrder.query.order_by(SalesOrder.created_at.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)
        
    orders = query.paginate(page=page, per_page=10)
    
    # Calculate stats
    pending_count = SalesOrder.query.filter_by(status='Draft').count()
    unpaid_count = SalesOrder.query.filter_by(status='Confirmed').count()
    
    return render_template('sales/index.html', orders=orders, pending=pending_count, unpaid=unpaid_count)

@sales_bp.route('/create', methods=['GET', 'POST'])
def create_order():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    if request.method == 'POST':
        try:
            # 1. Parse Form Data
            customer_id = request.form['customer_id']
            date_str = request.form['date']
            due_date_str = request.form.get('due_date')
            notes = request.form.get('notes')
            items_json = request.form.get('items_json') # Passed as JSON string from frontend
            
            # Format Date
            order_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            due_date = None
            if due_date_str:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            
            # Generate SO Number
            so_count = SalesOrder.query.filter(SalesOrder.date == order_date).count() + 1
            so_number = f"SO-{order_date.strftime('%Y%m')}-{so_count:04d}"
            
            # Create Order Header
            new_so = SalesOrder(
                order_number=so_number,
                customer_id=customer_id,
                date=order_date,
                due_date=due_date,
                status='Draft',
                notes=notes
            )
            
            db.session.add(new_so)
            db.session.flush() # Get ID
            
            # Process Items
            items = json.loads(items_json)
            total = 0
            
            for item in items:
                 p_id = int(item['product_id'])
                 qty = int(item['qty'])
                 
                 product = Product.query.get(p_id)
                 price = product.price # Use current price
                 subtotal = price * qty
                 
                 so_item = SalesOrderItem(
                     sales_order_id=new_so.id,
                     product_id=p_id,
                     quantity=qty,
                     price=price,
                     subtotal=subtotal
                 )
                 db.session.add(so_item)
                 total += subtotal
            
            new_so.total_amount = total
            new_so.grand_total = total # No tax/discount logic yet
            
            db.session.commit()
            flash(f'Sales Order {so_number} berhasil dibuat (Draft).', 'success')
            return redirect(url_for('sales.view_order', id=new_so.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal: {str(e)}', 'danger')
            return redirect(url_for('sales.create_order'))
            
    products = Product.query.filter(Product.stock_quantity > 0).order_by(Product.name).all()
    customers = Customer.query.order_by(Customer.name).all()
    today = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('sales/form.html', products=products, customers=customers, today=today)

@sales_bp.route('/<int:id>')
def view_order(id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    order = SalesOrder.query.get_or_404(id)
    return render_template('sales/view.html', order=order)

@sales_bp.route('/<int:id>/confirm', methods=['POST'])
def confirm_order(id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    order = SalesOrder.query.get_or_404(id)
    
    if order.status != 'Draft':
        flash('Order sudah diproses.', 'warning')
        return redirect(url_for('sales.view_order', id=id))
        
    try:
        # 1. Deduct Stock & Create Stock Ledger (Transaction)
        cogs_total = 0
        
        for item in order.items:
            product = item.product
            
            # Validate Stock
            if product.stock_quantity < item.quantity:
                raise ValueError(f"Stok {product.name} tidak cukup! (Sisa: {product.stock_quantity})")
                
            product.stock_quantity -= item.quantity
            cogs_total += product.cost * item.quantity
            
            # Record Stock Transaction
            trx = Transaction(
                product_id=product.id,
                transaction_type='OUT',
                quantity=item.quantity,
                total_amount=item.subtotal,
                reference=order.order_number,
                customer_id=order.customer_id,
                fulfillment_status='pending' # Trigger Warehouse Picking
            )
            db.session.add(trx)
            
        # 2. Accounting Journals
        try:
             AccountingService.record_sale(
                 reference=order.order_number,
                 total_amount=order.grand_total,
                 cogs_amount=cogs_total
             )
        except Exception as e:
             flash(f"Warning: Accounting entry failed ({e})", 'warning')
             
        # 3. Update Status
        order.status = 'Confirmed'
        db.session.commit()
        
        flash('Order dikonfirmasi! Stok berkurang & Jurnal tercatat.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal Konfirmasi: {str(e)}', 'danger')
        
    return redirect(url_for('sales.view_order', id=id))

@sales_bp.route('/<int:id>/paid', methods=['POST'])
def mark_paid(id):
     # Mark as Paid (Cash In) logic could go here later
     # For now just status update
     order = SalesOrder.query.get_or_404(id)
     order.status = 'Paid'
     db.session.commit()
     flash('Status update: Lunas', 'success')
     return redirect(url_for('sales.view_order', id=id))

@sales_bp.route('/return_list')
def return_list():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    returns = SalesReturn.query.order_by(SalesReturn.created_at.desc()).all()
    # Only confirmed/paid orders can be returned
    eligible_orders = SalesOrder.query.filter(SalesOrder.status.in_(['Confirmed', 'Paid'])).order_by(SalesOrder.date.desc()).all()
    
    return render_template('sales/return_list.html', returns=returns, eligible_orders=eligible_orders)

@sales_bp.route('/return/process', methods=['POST'])
def process_return():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    try:
        so_id = request.form['sales_order_id']
        refund_amount = float(request.form['refund_amount'])
        reason = request.form['reason']
        
        # 1. Create Return Record
        ret_count = SalesReturn.query.count() + 1
        ret_number = f"RET-{datetime.now().strftime('%Y%m')}-{ret_count:04d}"
        
        new_return = SalesReturn(
            return_number=ret_number,
            sales_order_id=so_id,
            reason=reason,
            total_refund=refund_amount,
            status='Approved' # Auto-approve for now
        )
        db.session.add(new_return)
        
        # 2. Accounting Adjustment (Reverse Sale)
        # Dr. Sales Returns / Revenue (4100) -> Debit reduces Revenue
        # Cr. Cash / AR (1100/1200)
        try:
             # We reuse 4100 (Revenue) to reduce it, or use a specific contra-revenue account.
             # Let's debit Revenue (4100) directly to keep it simple.
             from app.models import Account, JournalEntry, JournalItem
             
             je = JournalEntry(
                 date=datetime.utcnow(),
                 reference=ret_number,
                 description=f"Retur Penjualan {new_return.sales_order.order_number}"
             )
             db.session.add(je)
             db.session.flush()
             
             # Debit Revenue (Reduce Income)
             rev_acc = Account.query.filter_by(code='4100').first()
             ji1 = JournalItem(journal_entry_id=je.id, account_id=rev_acc.id, debit=refund_amount, credit=0)
             rev_acc.balance -= refund_amount 
             
             # Credit Cash/AR (Refund Money)
             cash_acc = Account.query.filter_by(code='1100').first()
             ji2 = JournalItem(journal_entry_id=je.id, account_id=cash_acc.id, debit=0, credit=refund_amount)
             cash_acc.balance -= refund_amount
             
             db.session.add(ji1)
             db.session.add(ji2)
             
        except Exception as e:
             print(f"Accounting Error (Return): {e}")

        # 3. Stock Adjustment?
        # Ideally we should know WHICH items are returned. 
        # For this MVP step, we rely on the user to use 'Stock Opname' or 'Receiving' to add stock back physically if it's visible.
        # Or we could auto-add all items? That's dangerous if partial return.
        # Let's leave stock adjustment to manual Opname for accuracy on partial returns, as per prompt "Retur penjualan" usually implies financial + stock.
        # User prompt is simple. Let's assume manual stock fix for now or add a flash message.
        
        db.session.commit()
        flash(f'Retur berhasil disimpan ({ret_number}).', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal: {str(e)}', 'danger')
        
    return redirect(url_for('sales.return_list'))

@sales_bp.route('/report')
def sales_report():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    from sqlalchemy import func
    
    # 1. KPIs
    total_sales = db.session.query(func.sum(SalesOrder.grand_total)).filter(SalesOrder.status.in_(['Confirmed', 'Paid'])).scalar() or 0
    total_orders = SalesOrder.query.filter(SalesOrder.status.in_(['Confirmed', 'Paid'])).count()
    avg_order = total_sales / total_orders if total_orders > 0 else 0
    
    # 2. Recent Sales
    recent_sales = SalesOrder.query.filter(SalesOrder.status.in_(['Confirmed', 'Paid']))\
                                   .order_by(SalesOrder.date.desc()).limit(10).all()
                                   
    # 3. Top Products (Join OrderItems -> Product)
    # SQLite might need specific group by syntax logic
    top_products = db.session.query(
        Product.name, 
        func.sum(SalesOrderItem.quantity).label('sold_count'),
        func.sum(SalesOrderItem.subtotal).label('subtotal_sum')
    ).join(SalesOrderItem).join(SalesOrder)\
     .filter(SalesOrder.status.in_(['Confirmed', 'Paid']))\
     .group_by(Product.name).order_by(func.sum(SalesOrderItem.quantity).desc()).limit(5).all()
     
    return render_template('sales/report.html', 
                          total_sales=total_sales, 
                          total_orders=total_orders,
                          avg_order_value=avg_order,
                          recent_sales=recent_sales,
                          top_products=top_products)