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
            try:
                import json
                session['features'] = json.loads(user.features) if user.features else []
            except:
                session['features'] = []
            
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

# --- Google OAuth Routes ---
from app import oauth
import os

# Konfigurasi Google Client
# Pastikan GOOGLE_CLIENT_ID dan GOOGLE_CLIENT_SECRET ada di .env
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@auth_bp.route('/google')
def google_login():
    # Redirect ke Google untuk login
    redirect_uri = url_for('auth.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@auth_bp.route('/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = token['userinfo']
        
        email = user_info['email']
        name = user_info.get('name', email.split('@')[0])
        
        # Cek apakah user sudah ada
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Buat user baru jika belum ada
            # Generate password acak karena login via Google
            import secrets
            random_password = secrets.token_hex(16)
            
            # Cek username conflict
            base_username = name.replace(" ", "").lower()
            username = base_username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(random_password),
                role='staff' # Default role
            )
            db.session.add(user)
            db.session.commit()
            flash(f'Akun berhasil dibuat! Login sebagai {username}.', 'success')
            
        # Login user
        session['user_id'] = user.id
        session['user_id'] = user.id
        session['role'] = user.role
        session['username'] = user.username
        try:
            import json
            session['features'] = json.loads(user.features) if user.features else []
        except:
            session['features'] = []
        
        flash(f'Selamat datang, {user.username}!', 'success')
        
        return redirect(url_for('web.index'))
        
    except Exception as e:
        flash(f'Gagal login Google: {str(e)}', 'danger')
        return redirect(url_for('auth.login_web'))

# Route untuk Logout
@auth_bp.route('/logout')
def logout():
    session.clear() # Hapus sesi
    flash('Anda berhasil logout.', 'info')
    return redirect(url_for('auth.login_web'))