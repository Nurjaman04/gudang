from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Customer, Interaction, Transaction, db
from datetime import datetime, date
from sqlalchemy import func

crm_bp = Blueprint('crm', __name__, url_prefix='/crm')

@crm_bp.route('/')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    # KPIs
    total_customers = Customer.query.count()
    new_this_month = Customer.query.filter(func.strftime('%Y-%m', Customer.joined_at) == datetime.utcnow().strftime('%Y-%m')).count()
    
    # Interactions
    pending_followups = Interaction.query.filter(
        Interaction.follow_up_date <= date.today(),
        Interaction.status == 'Open'
    ).count()
    
    recent_interactions = Interaction.query.order_by(Interaction.date.desc()).limit(5).all()
    
    # Top Customers by Spend (Simplified)
    # This requires joining Transaction
    top_customers = db.session.query(
        Customer, func.sum(Transaction.total_amount).label('total_spend')
    ).join(Transaction).filter(Transaction.transaction_type == 'OUT')\
     .group_by(Customer.id).order_by(func.sum(Transaction.total_amount).desc()).limit(5).all()
    
    return render_template('crm/dashboard.html', 
                          total_customers=total_customers,
                          new_this_month=new_this_month,
                          pending_followups=pending_followups,
                          recent_interactions=recent_interactions,
                          top_customers=top_customers)

@crm_bp.route('/customers')
def customer_list():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '')
    
    if query:
        customers = Customer.query.filter(
            (Customer.name.ilike(f'%{query}%')) | 
            (Customer.email.ilike(f'%{query}%'))
        ).paginate(page=page, per_page=10)
    else:
        customers = Customer.query.order_by(Customer.name).paginate(page=page, per_page=10)
        
    return render_template('crm/customer_list.html', customers=customers, query=query)

@crm_bp.route('/customers/add', methods=['POST'])
def add_customer():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    try:
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        c_type = request.form['type']
        
        nc = Customer(name=name, email=email, phone=phone, type=c_type)
        db.session.add(nc)
        db.session.commit()
        
        flash('Pelanggan berhasil ditambahkan.', 'success')
    except Exception as e:
        flash(f'Gagal: {str(e)}', 'danger')
        
    return redirect(url_for('crm.customer_list'))

@crm_bp.route('/customers/<int:id>')
def customer_detail(id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    c = Customer.query.get_or_404(id)
    interactions = Interaction.query.filter_by(customer_id=id).order_by(Interaction.date.desc()).all()
    transactions = Transaction.query.filter_by(customer_id=id).order_by(Transaction.created_at.desc()).all()
    
    # Calculate stats
    total_spend = sum(t.total_amount for t in transactions if t.transaction_type == 'OUT')
    
    return render_template('crm/customer_detail.html', customer=c, interactions=interactions, transactions=transactions, total_spend=total_spend)

@crm_bp.route('/interactions/add', methods=['POST'])
def add_interaction():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    try:
        c_id = request.form['customer_id']
        i_type = request.form['type']
        notes = request.form['notes']
        date_str = request.form.get('follow_up_date')
        
        follow_up = None
        if date_str:
            follow_up = datetime.strptime(date_str, '%Y-%m-%d').date()
            
        ni = Interaction(
            customer_id=c_id,
            type=i_type,
            notes=notes,
            follow_up_date=follow_up
        )
        db.session.add(ni)
        db.session.commit()
        
        flash('Interaksi dicatat.', 'success')
        return redirect(url_for('crm.customer_detail', id=c_id))
    except Exception as e:
        flash(f'Gagal: {str(e)}', 'danger')
        return redirect(url_for('crm.customer_list'))

@crm_bp.route('/interaction/complete/<int:id>')
def complete_interaction(id):
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    i = Interaction.query.get_or_404(id)
    i.status = 'Closed'
    db.session.commit()
    flash('Follow-up selesai.', 'success')
    return redirect(request.referrer or url_for('crm.dashboard'))
