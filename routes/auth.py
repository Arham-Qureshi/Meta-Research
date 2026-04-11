from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, limiter
from models import User
from errors import api_success, api_error, ValidationError, ConflictError, AuthenticationError
from validators import require_json, validate_email, validate_password, validate_string

bp = Blueprint('auth', __name__)

@bp.route('/signup', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
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
                return api_error(msg, 400)
            flash(msg, 'error')
            return redirect(url_for('auth.signup'))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            msg = 'Username or email already exists.'
            if request.is_json:
                return api_error(msg, 409)
            flash(msg, 'error')
            return redirect(url_for('auth.signup'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        if request.is_json:
            return api_success(
                {'username': user.username, 'email': user.email},
                message='Account created successfully',
                status=201,
            )
        return redirect(url_for('pages.index'))
    return render_template('signup.html')


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
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
                return api_success(
                    {'username': user.username, 'email': user.email},
                    message='Login successful',
                )
            return redirect(url_for('pages.index'))
        msg = 'Invalid email or password.'
        if request.is_json:
            return api_error(msg, 401)
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
    if current_user.is_authenticated:
        return api_success({
            'authenticated': True,
            'username': current_user.username,
            'email': current_user.email,
        })
    return api_success({'authenticated': False})


@bp.route('/api/signup', methods=['POST'])
@limiter.limit('3 per minute')
@require_json('username', 'email', 'password')
def api_signup():
    data = request.get_json()

    username = validate_string(data['username'], 'Username', min_len=2, max_len=80)
    email = validate_email(data['email'])
    password = validate_password(data['password'])

    if User.query.filter((User.username == username) | (User.email == email)).first():
        raise ConflictError('Username or email already exists.')

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)

    return api_success(
        {'username': user.username, 'email': user.email},
        message='Account created successfully',
        status=201,
    )


@bp.route('/api/login', methods=['POST'])
@limiter.limit('5 per minute')
@require_json('email', 'password')
def api_login():
    data = request.get_json()
    email = data['email'].strip()
    password = data['password']

    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        login_user(user)
        return api_success(
            {'username': user.username, 'email': user.email},
            message='Login successful',
        )
    raise AuthenticationError('Invalid email or password.')


@bp.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return api_success(message='Logged out successfully.')
