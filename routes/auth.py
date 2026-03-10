"""
routes/auth.py — Authentication routes.

Handles signup, login, logout, and current-user info.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User

bp = Blueprint('auth', __name__)


@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('pages.index'))
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')

        if not username or not email or not password:
            msg = 'All fields are required.'
            if request.is_json:
                return jsonify({'error': msg}), 400
            flash(msg, 'error')
            return redirect(url_for('auth.signup'))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            msg = 'Username or email already exists.'
            if request.is_json:
                return jsonify({'error': msg}), 409
            flash(msg, 'error')
            return redirect(url_for('auth.signup'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        if request.is_json:
            return jsonify({'message': 'Account created successfully', 'username': user.username}), 201
        return redirect(url_for('pages.index'))
    return render_template('signup.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('pages.index'))
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        email = data.get('email', '').strip()
        password = data.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            if request.is_json:
                return jsonify({'message': 'Login successful', 'username': user.username}), 200
            return redirect(url_for('pages.index'))
        msg = 'Invalid email or password.'
        if request.is_json:
            return jsonify({'error': msg}), 401
        flash(msg, 'error')
        return redirect(url_for('auth.login'))
    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('pages.index'))


@bp.route('/api/me')
def api_me():
    """Return current user info (or anonymous)."""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'username': current_user.username,
            'email': current_user.email,
        })
    return jsonify({'authenticated': False})
