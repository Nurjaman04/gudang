from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Route untuk Login Halaman Web
@auth_bp.route('/login', methods=['GET', 'POST'])
def login_web():
    # Jika sudah login, lempar ke dashboard
    if 'user_id' in session:
        return redirect(url_for('web.index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Cari user di database
        user = User.query.filter_by(username=username).first()
        
        # Cek Password
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            flash(f'Selamat datang, {user.username}!', 'success')
            return redirect(url_for('web.index'))
        else:
            flash('Username atau Password salah!', 'danger')
            
    return render_template('login.html')

# Route untuk Registrasi User Baru
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Jika sudah login, logout dulu atau redirect
    if 'user_id' in session:
        return redirect(url_for('web.index'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Validasi
        if password != confirm_password:
            flash('Password tidak cocok!', 'danger')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan!', 'danger')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Email sudah terdaftar!', 'danger')
            return redirect(url_for('auth.register'))

        # Buat User Baru
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password, role='staff')
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registrasi berhasil! Silakan login.', 'success')
        return redirect(url_for('auth.login_web'))

    return render_template('register.html')

    return render_template('register.html')

# --- Google OAuth Routes (Placeholder Implementation) ---
# Note: Requires 'authlib' or 'flask-dance' for real production usage.
# For now, we simulate the flow or provide a stub.

@auth_bp.route('/google')
def google_login():
    # In a real app, this would redirect to Google's OAuth URL
    # return oauth.google.authorize_redirect(url_for('auth.google_callback', _external=True))
    
    # Simulation for Demo purposes (since we might not have API keys set up)
    flash("Fitur Google Login memerlukan konfigurasi API Key (CLIENT_ID).", "warning")
    return redirect(url_for('auth.login_web'))

@auth_bp.route('/google/callback')
def google_callback():
    # token = oauth.google.authorize_access_token()
    # verify user info...
    # create user if not exists...
    return redirect(url_for('web.index'))

# Route untuk Logout
@auth_bp.route('/logout')
def logout():
    session.clear() # Hapus sesi
    flash('Anda berhasil logout.', 'info')
    return redirect(url_for('auth.login_web'))