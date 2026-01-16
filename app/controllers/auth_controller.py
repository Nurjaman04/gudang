from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Route untuk Login Halaman Web
@auth_bp.route('/login', methods=['GET', 'POST'])
def login_web():
    # Jika sudah login, lempar ke dashboard
    if 'user_id' in session:
        return redirect(url_for('web.dashboard'))

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
            return redirect(url_for('web.dashboard'))
        else:
            flash('Username atau Password salah!', 'danger')
            
    return render_template('login.html')

# Route untuk Logout
@auth_bp.route('/logout')
def logout():
    session.clear() # Hapus sesi
    flash('Anda berhasil logout.', 'info')
    return redirect(url_for('auth.login_web'))