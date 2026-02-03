from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Account, JournalEntry, JournalItem, db
from datetime import datetime
from sqlalchemy import func

accounting_bp = Blueprint('accounting', __name__, url_prefix='/accounting')

@accounting_bp.route('/')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    # Simple Metrics
    total_assets = db.session.query(func.sum(Account.balance)).filter(Account.type == 'Asset').scalar() or 0
    total_revenue = db.session.query(func.sum(Account.balance)).filter(Account.type == 'Revenue').scalar() or 0
    total_expenses = db.session.query(func.sum(Account.balance)).filter(Account.type == 'Expense').scalar() or 0
    net_profit = total_revenue - total_expenses
    
    recent_journals = JournalEntry.query.order_by(JournalEntry.created_at.desc()).limit(5).all()
    
    return render_template('accounting/dashboard.html', 
                          total_assets=total_assets,
                          net_profit=net_profit,
                          recent_journals=recent_journals)

@accounting_bp.route('/coa')
def chart_of_accounts():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    accounts = Account.query.order_by(Account.code).all()
    return render_template('accounting/coa.html', accounts=accounts)

@accounting_bp.route('/journal')
def journal_entries():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    entries = JournalEntry.query.order_by(JournalEntry.date.desc(), JournalEntry.id.desc()).all()
    return render_template('accounting/journal.html', entries=entries)

@accounting_bp.route('/balance_sheet')
def balance_sheet():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    assets = Account.query.filter_by(type='Asset').all()
    liabilities = Account.query.filter_by(type='Liability').all()
    equity = Account.query.filter_by(type='Equity').all()
    
    total_assets = sum(a.balance for a in assets)
    total_liabilities = sum(a.balance for a in liabilities)
    total_equity = sum(a.balance for a in equity)
    
    # Calculate Current Year Earnings (Revenue - Expense) to balance the sheet implicitly
    revenue = db.session.query(func.sum(Account.balance)).filter(Account.type == 'Revenue').scalar() or 0
    expense = db.session.query(func.sum(Account.balance)).filter(Account.type == 'Expense').scalar() or 0
    current_earnings = revenue - expense
    
    check_balance = total_assets - (total_liabilities + total_equity + current_earnings)
    
    return render_template('accounting/balance_sheet.html',
                          assets=assets, liabilities=liabilities, equity=equity,
                          current_earnings=current_earnings,
                          total_assets=total_assets, 
                          total_le=total_liabilities + total_equity + current_earnings)

@accounting_bp.route('/profit_loss')
def profit_loss():
    if 'user_id' not in session: return redirect(url_for('auth.login_web'))
    
    revenues = Account.query.filter_by(type='Revenue').all()
    expenses = Account.query.filter_by(type='Expense').all() # COGS included here as Expense type for simplicity in this model
    
    total_revenue = sum(a.balance for a in revenues)
    total_expense = sum(a.balance for a in expenses)
    net_profit = total_revenue - total_expense
    
    return render_template('accounting/profit_loss.html',
                          revenues=revenues, expenses=expenses,
                          total_revenue=total_revenue, total_expense=total_expense,
                          net_profit=net_profit)
