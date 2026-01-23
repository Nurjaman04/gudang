from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User
from app import db
from werkzeug.security import generate_password_hash
import json

user_bp = Blueprint('user', __name__, url_prefix='/users')

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('auth.login_web'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') not in ['manager', 'admin']:
            flash('Anda tidak memiliki akses ke halaman ini.', 'danger')
            return redirect(url_for('web.index'))
        return f(*args, **kwargs)
    return decorated_function

@user_bp.route('/')
@login_required
@admin_required
def index():
    users = User.query.all()
    # Parse features for display if needed, or do it in template
    for user in users:
        if user.features:
            try:
                user.feature_list = json.loads(user.features)
            except:
                user.feature_list = []
        else:
            user.feature_list = []
            
    return render_template('users/index.html', users=users)

@user_bp.route('/contact') # Placeholder if needed, but not in plan
def contact():
    return "Contact"

@user_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        # Get selected features
        selected_features = request.form.getlist('features')
        features_json = json.dumps(selected_features)
        
        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan!', 'danger')
            return redirect(url_for('user.new'))
            
        if User.query.filter_by(email=email).first():
            flash('Email sudah digunakan!', 'danger')
            return redirect(url_for('user.new'))
            
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username, 
            email=email, 
            password_hash=hashed_password, 
            role=role,
            features=features_json
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('User berhasil ditambahkan!', 'success')
        return redirect(url_for('user.index'))
        
    return render_template('users/form.html', user=None)

@user_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.role = request.form['role']
        
        # Password update only if provided
        password = request.form.get('password')
        if password:
            user.password_hash = generate_password_hash(password)
            
        # Features
        selected_features = request.form.getlist('features')
        user.features = json.dumps(selected_features)
        
        try:
            db.session.commit()
            flash('User berhasil diperbarui!', 'success')
            return redirect(url_for('user.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {e}', 'danger')
            
    # Load existing features
    current_features = []
    if user.features:
        try:
            current_features = json.loads(user.features)
        except:
            pass
            
    return render_template('users/form.html', user=user, current_features=current_features)

@user_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(id):
    user = User.query.get_or_404(id)
    
    if user.id == session['user_id']:
        flash('Anda tidak dapat menghapus akun sendiri!', 'danger')
        return redirect(url_for('user.index'))
        
    db.session.delete(user)
    db.session.commit()
    flash('User berhasil dihapus.', 'success')
    return redirect(url_for('user.index'))
