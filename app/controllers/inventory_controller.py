from flask import Blueprint, request, jsonify, redirect, url_for, flash, session, render_template
from app.models import Product, Transaction, MaterialRequest, Warehouse, Category, Unit, InventoryStock, PurchaseOrder, PurchaseOrderItem
from app import db
from datetime import datetime
from sqlalchemy import func
import random

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')

# --- [BARU] Endpoint Khusus untuk Form Web ---
@inventory_bp.route('/add_web', methods=['POST'])
def add_product_web():
    # Cek login (Keamanan)
    if 'user_id' not in session:
        return redirect(url_for('auth.login_web'))
    
    if session.get('role') not in ['admin', 'manager'] and 'inventory' not in session.get('features', []):
        flash('Anda tidak memiliki akses ke fitur ini.', 'danger')
        return redirect(url_for('web.index'))

    try:
        # Ambil data dari form HTML
        sku = request.form['sku']
        name = request.form['name']
        price = float(request.form['price'])
        cost = float(request.form['cost'])
        stock = int(request.form['stock'])
        min_stock = int(request.form['min_stock'])
        category = request.form.get('category', 'General')
        unit = request.form.get('unit', 'pcs')
        
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
            min_stock_threshold=min_stock,
            category=category,
            unit=unit
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
from flask import Blueprint, request, jsonify, redirect, url_for, flash, session, render_template
from app.models import Product, Transaction
from app import db

# ... (Biarkan endpoint add_product_web yang tadi)

# --- [BARU] Endpoint untuk Restock Lewat Web ---
@inventory_bp.route('/restock_web', methods=['POST'])
def restock_product_web():
    if 'user_id' not in session:
        return redirect(url_for('auth.login_web'))

    if session.get('role') not in ['admin', 'manager'] and 'inventory' not in session.get('features', []):
        flash('Anda tidak memiliki akses ke fitur ini.', 'danger')
        return redirect(url_for('web.index'))

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
        
    return redirect(url_for('web.inventory'))

@inventory_bp.route('/process_receiving', methods=['POST'])
def receiving_process():
    if 'user_id' not in session:
        return redirect(url_for('auth.login_web'))

    if session.get('role') not in ['admin', 'manager'] and 'inventory' not in session.get('features', []):
        flash('Anda tidak memiliki akses ke fitur ini.', 'danger')
        return redirect(url_for('web.index'))

    try:
        import json
        items_json = request.form.get('items_json')
        supplier = request.form['supplier']
        ref = request.form['reference']
        print_address = request.form.get('print_address')
        
        # New Inputs for Smart Inventory
        expiry_str = request.form.get('expiry_date') # Shared expiry for now, or per item if extended
        expiry_date = None
        if expiry_str:
             from datetime import datetime
             expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date()

        if not items_json:
            raise ValueError("Tidak ada item yang diterima")

        items = json.loads(items_json)
        
        # Group ID for Printing (Optional, using Reference is easier)
        
        from app.services.inventory_engine import SmartInventoryEngine
        from app.services.accounting_service import AccountingService

        created_trxs = []

        for item in items:
            p_id = item['product_id']
            qty = int(item['quantity'])
            cost = float(item.get('cost', 0)) # Item specific cost
            
            product = Product.query.get(p_id)
            if not product: continue

            # 1. Update Stock & Create Batch
            SmartInventoryEngine.process_inbound(
                product_id=product.id,
                quantity=qty,
                cost_price=cost if cost > 0 else product.cost,
                expiry_date=expiry_date,
                auto_commit=False 
            )
            
            # Update Master Stock
            product.stock_quantity += qty
            
            # 2. Record Transaction
            trx = Transaction(
                product_id=product.id,
                transaction_type='IN',
                quantity=qty,
                total_amount=0, 
                supplier=supplier,    
                reference=ref         
            )
            db.session.add(trx)
            db.session.flush() # Get ID
            created_trxs.append(trx)

            # 3. Accounting
            try:
                 total_purchase_cost = (cost if cost > 0 else product.cost) * qty
                 AccountingService.record_purchase(
                     reference=ref or f"RCV-{trx.id}",
                     amount=total_purchase_cost,
                     supplier=supplier
                 )
            except Exception as e:
                 print(f"Accounting Error (Purchase): {e}")

        # Save print address
        if print_address:
            session['last_print_address'] = print_address
            session[f'print_addr_ref_{ref}'] = print_address # Key by Reference

        db.session.commit()
        
        flash(f'Penerimaan {len(items)} item barang berhasil. Silakan cetak bukti.', 'success')
        return redirect(url_for('inventory.receiving_success_by_ref', ref=ref))
        
    except Exception as e:
        db.session.rollback()

        flash(f'Gagal: {str(e)}', 'danger')
        return redirect(url_for('web.receiving_page'))

@inventory_bp.route('/receiving/success/<int:id>')
def receiving_success(id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    # Legacy Support or Single Item view
    trx = Transaction.query.get_or_404(id)
    print_address = session.get(f'print_addr_{id}') or session.get('last_print_address')
    
    # Pass as list
    return render_template('inventory/receipt_success.html', transactions=[trx], print_address=print_address, now=datetime.now())

@inventory_bp.route('/receiving/success/ref/<path:ref>')
def receiving_success_by_ref(ref):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    # Fetch latest transactions with this reference
    # Limit to reasonable number to avoid fetching old history if ref reused
    transactions = Transaction.query.filter_by(reference=ref, transaction_type='IN').order_by(Transaction.id.desc()).limit(50).all()
    
    if not transactions:
        flash('Data transaksi tidak ditemukan untuk dicetak.', 'warning')
        return redirect(url_for('web.inventory'))
        
    print_address = session.get(f'print_addr_ref_{ref}') or session.get('last_print_address')
    
    # Determine Supplier from first trx
    supplier_name = transactions[0].supplier if transactions else '-'
    
    return render_template('inventory/receipt_success.html', transactions=transactions, print_address=print_address, now=datetime.now(), ref=ref, supplier_name=supplier_name)


@inventory_bp.route('/api/get_request_details', methods=['GET'])
def get_request_details():
    if 'user_id' not in session: 
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    req_no = request.args.get('request_number')
    if not req_no:
        return jsonify({'success': False, 'message': 'Masukkan No. Request'}), 400

    # Search exact match
    req = MaterialRequest.query.filter_by(request_number=req_no).first()
    
    if not req:
        return jsonify({'success': False, 'message': 'Data Request tidak ditemukan.'}), 404
        
    if req.status != 'PENDING':
        return jsonify({'success': False, 'message': f'Request ini sudah {req.status}.'}), 400

    return jsonify({
        'success': True,
        'data': {
            'branch_name': req.branch_name,
            'product_id': req.product_id,
            'quantity': req.quantity,
            'reference': req.request_number
        }
    })

# --- [BARU] Endpoint Fetch PO Details ---
@inventory_bp.route('/api/get_po_details', methods=['GET'])
def get_po_details():
    if 'user_id' not in session: 
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    po_number = request.args.get('po_number')
    if not po_number:
        return jsonify({'success': False, 'message': 'Masukkan No. PO'}), 400
        
    po = PurchaseOrder.query.filter_by(po_number=po_number).first()
    if not po:
        return jsonify({'success': False, 'message': 'PO tidak ditemukan.'}), 404
        
    items_data = []
    for item in po.items:
        remaining = item.quantity - item.received_qty
        if remaining > 0:
            items_data.append({
                'product_id': item.product_id,
                'sku': item.product.sku,
                'name': item.product.name,
                'ordered_qty': item.quantity,
                'received_qty': item.received_qty,
                'remaining_qty': remaining,
                'unit_cost': item.unit_cost
            })
            
    return jsonify({
        'success': True,
        'supplier': po.supplier.name if po.supplier else '-',
        'items': items_data
    })

# --- [BARU] Endpoint Transfer Antar Cabang ---

@inventory_bp.route('/transfer', methods=['GET'])
def transfer_page():
    if 'user_id' not in session:
        return redirect(url_for('auth.login_web'))
    
    if session.get('role') not in ['admin', 'manager'] and 'inventory' not in session.get('features', []):
        flash('Anda tidak memiliki akses ke fitur ini.', 'danger')
        return redirect(url_for('web.index'))
        
    products = Product.query.order_by(Product.name).all()
    warehouses = Warehouse.query.order_by(Warehouse.name).all()
    pending_requests = MaterialRequest.query.filter_by(status='PENDING').order_by(MaterialRequest.created_at.desc()).all()
    
    # Get Transfer History (Explicit TF)
    transfers = Transaction.query.filter(Transaction.reference.like('TF-%')).order_by(Transaction.created_at.desc()).limit(20).all()
    
    return render_template('transfer.html', products=products, warehouses=warehouses, requests=pending_requests, transfers=transfers)

@inventory_bp.route('/request_material', methods=['POST'])
def request_material():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))

    try:
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        branch_name = request.form['branch_name']
        
        # Generate Auto Request Number
        # Format: REQ-YYYYMMDD-Random4Digit
        req_date = datetime.now().strftime('%Y%m%d')
        req_rand = random.randint(1000, 9999)
        req_no = f"REQ-{req_date}-{req_rand}"
        
        new_request = MaterialRequest(
            request_number=req_no,
            product_id=product_id,
            quantity=quantity,
            branch_name=branch_name,
            status='PENDING'
        )
        
        db.session.add(new_request)
        db.session.commit()
        
        flash(f'Request Material {req_no} berhasil dibuat! Menunggu konfirmasi dari {branch_name}.', 'success')
        
        # Check action button
        action = request.form.get('action')
        if action == 'print':
            return redirect(url_for('inventory.print_material_request', req_id=new_request.id))
        
    except Exception as e:
        flash(f'Gagal membuat request: {str(e)}', 'danger')
        
    return redirect(url_for('inventory.transfer_page'))

@inventory_bp.route('/print_request/<int:req_id>')
def print_material_request(req_id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    req = MaterialRequest.query.get_or_404(req_id)
    return render_template('print_request.html', req=req)

@inventory_bp.route('/process_request/<int:req_id>', methods=['POST'])
def process_request(req_id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    action = request.form.get('action') # 'approve' or 'reject'
    req = MaterialRequest.query.get_or_404(req_id)
    
    if action == 'reject':
        req.status = 'REJECTED'
        db.session.commit()
        flash('Request ditolak.', 'warning')
        return redirect(url_for('inventory.transfer_page'))
        
    # If Approve, we process it as a TRANSFER_IN (We are receiving the item requested)
    # OR TRANSFER_OUT (We are sending the item requested)
    # Context matters: 
    # If "Request Material" means "I want goods from Branch X", then Branch X sees this and "Approves" it to SEND goods (Transfer Out).
    # Currently we are a single system. So if I create a request "Ask Bandung for 10 items", 
    # I am the requester. 
    # If I "Process" it, it implies the goods have arrived? Or that I am fulfilling it?
    
    # Let's assume this system manages the Central Warehouse.
    # If "Branch Name" is "Target Branch", then "Request Material" = "Ask Branch to send to HQ".
    # Then "Approve" = "Goods arrived at HQ" (Transfer In).
    
    # OR
    
    # "Request Material" = "Branch asks HQ for goods".
    # Then "Approve" = "HQ sends goods to Branch" (Transfer Out).
    
    # Given the user said "material request nya dalam pemindahan barang", and typical WMS:
    # Warehouse users usually create requests to REPLENISH from branches/suppliers, OR Branches request FROM Warehouse.
    
    # Let's assume: Users use this app to manage ONE warehouse (e.g. HQ).
    # Scenario A: HQ requests goods from 'Surabaya'. Status Pending.
    # When goods arrive, we click "Finish/Receive". -> Transfer In.
    
    try:
        if action == 'approve':
            # We assume this means the request is fulfilled -> We RECEIVE the items (Transfer In)
            # Logic: Requesting from Branch -> Branch Sends -> We Receive.
            
            product = Product.query.get(req.product_id)
            
            # Add Stock
            product.stock_quantity += req.quantity
            
            # Log Transaction
            trx = Transaction(
                product_id=product.id,
                transaction_type='TRANSFER_IN',
                quantity=req.quantity,
                total_amount=0,
                reference=req.request_number or f"REQ-{req.id}",
                branch_name=req.branch_name
            )
            
            req.status = 'PROCESSED'
            db.session.add(trx)
            db.session.commit()
            
            flash(f'Barang diterima dari {req.branch_name}. Stok bertambah {req.quantity}. (Ref: {trx.reference})', 'success')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        
    return redirect(url_for('inventory.transfer_page'))

@inventory_bp.route('/process_transfer', methods=['POST'])
def process_transfer():
    if 'user_id' not in session:
        return redirect(url_for('auth.login_web'))



    try:
        # New Logic: Warehouse to Warehouse
        source_id = int(request.form['source_warehouse_id'])
        dest_id = int(request.form['destination_warehouse_id'])
        product_id = int(request.form['product_id'])
        quantity = int(request.form['quantity'])
        reference = request.form.get('reference', f"TF-{datetime.now().strftime('%Y%m%d%H%M')}")
        notes = request.form.get('notes', '')

        if source_id == dest_id:
            flash('Gudang asal dan tujuan tidak boleh sama.', 'warning')
            return redirect(url_for('inventory.transfer_page'))

        product = Product.query.get_or_404(product_id)
        
        # 1. Validation: Check Source Stock
        source_stock = InventoryStock.query.filter_by(warehouse_id=source_id, product_id=product_id).first()
        
        if not source_stock or source_stock.quantity < quantity:
            flash(f'Gagal! Stok di gudang asal tidak cukup. Sisa: {source_stock.quantity if source_stock else 0}', 'danger')
            return redirect(url_for('inventory.transfer_page'))

        # 2. Execute Transfer (Atomic)
        # Reduce Source
        source_stock.quantity -= quantity
        
        # Increase Dest (Create if not exists)
        dest_stock = InventoryStock.query.filter_by(warehouse_id=dest_id, product_id=product_id).first()
        if not dest_stock:
            dest_stock = InventoryStock(warehouse_id=dest_id, product_id=product_id, quantity=0)
            db.session.add(dest_stock)
        
        dest_stock.quantity += quantity
        
        # 3. Record Transactions (OUT from Source, IN to Dest) -- OR Single Transfer Record
        # To maintain checking history, we record 2 transactions or 1 specialized.
        # Let's record 2 for clear flow in movement history.
        
        source_wh = Warehouse.query.get(source_id)
        dest_wh = Warehouse.query.get(dest_id)

        # OUT Transaction
        trx_out = Transaction(
            product_id=product_id,
            transaction_type='OUT', # Or 'TRANSFER_OUT'
            quantity=quantity,
            total_amount=0,
            reference=reference,
            branch_name=f"Transfer to {dest_wh.name}", # abusing branch_name for context
            supplier=f"From {source_wh.name}" # abuse supplier field strictly for context
        )
        
        # IN Transaction
        trx_in = Transaction(
            product_id=product_id,
            transaction_type='IN', # Or 'TRANSFER_IN'
            quantity=quantity,
            total_amount=0,
            reference=reference,
            branch_name=f"Transfer from {source_wh.name}",
            supplier=f"To {dest_wh.name}"
        )
        
        db.session.add(trx_out)
        db.session.add(trx_in)
        
        db.session.commit()
        
        flash(f'Transfer berhasil! {quantity} {product.unit} dipindahkan dari {source_wh.name} ke {dest_wh.name}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal Transfer: {str(e)}', 'danger')
        
    return redirect(url_for('inventory.transfer_page'))

@inventory_bp.route('/print_transfer/<int:trx_id>')
def print_transfer(trx_id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    trx = Transaction.query.get_or_404(trx_id)
    return render_template('print_transfer.html', trx=trx)

# --- [BARU] Laporan Stock Ageing (Smart Inventory) ---
@inventory_bp.route('/aging_report')
def aging_report():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    # Check permissions
    if session.get('role') not in ['admin', 'manager'] and 'inventory' not in session.get('features', []):
        flash('Anda tidak memiliki akses ke fitur ini.', 'danger')
        return redirect(url_for('web.index'))

    from app.services.inventory_engine import SmartInventoryEngine
    
    # Get Aging Data
    aging_data = SmartInventoryEngine.get_stock_ageing_report()
    
    # Calculate Total Valuation
    total_valuation = SmartInventoryEngine.calculate_valuation_fifo()
    
    return render_template('inventory_aging.html', 
                           aging_data=aging_data, 
                           total_valuation=total_valuation)

# --- [BARU] Stock Opname Feature ---


@inventory_bp.route('/opname_form')
def opname_form():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    products = Product.query.order_by(Product.rack_location).all()
    warehouses = Warehouse.query.all()
    # Auto-ref
    ref = f"OPN-{datetime.now().strftime('%Y%m%d%H%M')}"
    return render_template('opname.html', products=products, warehouses=warehouses, ref_number=ref)

@inventory_bp.route('/process_opname', methods=['POST'])
def process_opname():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    try:
        ref = request.form['reference']
        notes = request.form.get('notes', '')
        
        # Iterate through submitted products
        # Form structure: real_qty_{product_id}
        
        updated_count = 0
        
        for key, value in request.form.items():
            if key.startswith('real_qty_') and value:
                product_id = int(key.split('_')[2])
                real_qty = int(value)
                
                product = Product.query.get(product_id)
                system_qty = product.stock_quantity
                
                diff = real_qty - system_qty
                
                if diff != 0:
                    # Adjustment needed
                    
                    # 1. Update Master Stock
                    product.stock_quantity = real_qty
                    
                    # 2. Create Transaction (Adjustment)
                    # Diff > 0 means FOUND extra items (IN)
                    # Diff < 0 means LOST items (OUT or LOSS)
                    # We just label it 'OPNAME' and store the signed quantity or handle strictly
                    
                    # Store absolute quantity for transaction record usually, BUT
                    # For accounting, we need to know if it's + or -
                    # Let's simple use 'OPNAME' and store the DIFF as quantity (can be negative? No, usually quantity is unsigned in many systems, 
                    # but check data type. If signed allowed fine. If not, use Types 'OPNAME_IN' / 'OPNAME_OUT')
                    
                    # DB Schema: quantity is Integer. SQLite allows negative.
                    # But Logic usually: Transaction Type defines direction.
                    
                    t_type = 'OPNAME'
                    
                    trx = Transaction(
                        product_id=product.id,
                        transaction_type=t_type,
                        quantity=abs(diff), # Store magnitude
                        total_amount=0, # Adjustment has 0 revenue/cost usually, or calculated
                        reference=ref,
                        supplier=f"System: {system_qty} -> Real: {real_qty}", # Abuse supplier field for notes
                        branch_name=notes
                    )
                    
                    # Special handling: if diff is negative, it's effectively an OUT equivalent for stock calc
                    # But we already forced product.stock_quantity = real_qty.
                    # The transaction log allows us to reconstruct.
                    # If we used the transaction to DRIVE the stock, we would add/subtract `diff`.
                    # Since we Force Set, the transaction is just a Receipt/Log.
                    
                    db.session.add(trx)
                    updated_count += 1
                    
                    # --- ACCOUNTING HOOK (ADJUSTMENT) ---
                    try:
                        from app.services.accounting_service import AccountingService
                        # diff is Real - System.
                        # If diff < 0 (Real < System): LOSS (Missing stock). is_loss=True
                        # If diff > 0 (Real > System): GAIN (Found stock). is_loss=False
                        is_loss = diff < 0
                        amount_abs = abs(diff) * product.cost # Valuation based on cost
                        
                        AccountingService.record_adjustment(
                            reference=f"{ref} ({product.sku})",
                            amount=amount_abs,
                            is_loss=is_loss
                        )
                    except Exception as e:
                        print(f"Accounting Error (Opname): {e}")
        
        db.session.commit()
        
        if updated_count > 0:
            flash(f'Stock Opname Selesai! {updated_count} produk disesuaikan.', 'success')
        else:
            flash('Tidak ada perbedaan stok yang ditemukan.', 'info')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error Opname: {str(e)}', 'danger')
        
    return redirect(url_for('web.inventory'))

# --- INVENTORY MANAGEMENT FEATURES ---

@inventory_bp.route('/attributes')
def manage_attributes():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    categories = Category.query.order_by(Category.name).all()
    units = Unit.query.order_by(Unit.name).all()
    warehouses = Warehouse.query.order_by(Warehouse.name).all()
    
    return render_template('inventory/attributes.html', categories=categories, units=units, warehouses=warehouses)

@inventory_bp.route('/attributes/add_category', methods=['POST'])
def add_category():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    try:
        name = request.form['name']
        desc = request.form.get('description')
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name, description=desc))
            db.session.commit()
            flash('Kategori ditambahkan.', 'success')
        else:
            flash('Kategori sudah ada.', 'warning')
    except Exception as e:
        flash(f'Gagal: {e}', 'danger')
    return redirect(url_for('inventory.manage_attributes'))

@inventory_bp.route('/attributes/add_unit', methods=['POST'])
def add_unit():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    try:
        name = request.form['name']
        if not Unit.query.filter_by(name=name).first():
            db.session.add(Unit(name=name))
            db.session.commit()
            flash('Satuan ditambahkan.', 'success')
        else:
            flash('Satuan sudah ada.', 'warning')
    except Exception as e:
        flash(f'Gagal: {e}', 'danger')
    return redirect(url_for('inventory.manage_attributes'))

@inventory_bp.route('/attributes/add_warehouse', methods=['POST'])
def add_warehouse():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    try:
        name = request.form['name']
        loc = request.form.get('location')
        w_type = request.form.get('type', 'physical')
        
        db.session.add(Warehouse(name=name, location=loc, type=w_type))
        db.session.commit()
        flash('Gudang berhasil dibuat.', 'success')
    except Exception as e:
        flash(f'Gagal: {e}', 'danger')
    return redirect(url_for('inventory.manage_attributes'))

@inventory_bp.route('/stock_card/<int:product_id>')
def stock_card(product_id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    product = Product.query.get_or_404(product_id)
    
    # Get transactions sorted by date
    # Optional: Filter by Warehouse if we implement that fully.
    # Currently viewing GLOBAL stock movement.
    transactions = Transaction.query.filter_by(product_id=product_id)\
        .order_by(Transaction.created_at.desc()).limit(100).all()
        
    # Warehouse Stocks breakdown
    # Make sure we have stocks for this product in all warehouses
    # Query InventoryStock
    stocks = InventoryStock.query.filter_by(product_id=product_id).all()
    
    return render_template('inventory/stock_card.html', product=product, transactions=transactions, stocks=stocks)

@inventory_bp.route('/report/movements')
def movement_history():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    products = Product.query.order_by(Product.name).all()
    
    # Filter
    p_id = request.args.get('product_id', type=int)
    
    query = Transaction.query.order_by(Transaction.created_at.desc())
    if p_id:
        query = query.filter_by(product_id=p_id)
        
    transactions = query.limit(200).all()
    
    return render_template('inventory/movement_history.html', transactions=transactions, products=products, selected_product=p_id)