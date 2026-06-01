from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from ..models import db, User, AboutProfile

auth_bp = Blueprint('auth', __name__)


def _get_contact_email():
    profile = AboutProfile.query.first()
    return profile.email if profile and profile.email else 'admin@shop.local'


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        is_email = '@' in identifier

        if is_email:
            user = User.query.filter_by(email=identifier.lower()).first()
        else:
            user = User.query.filter_by(username=identifier).first()

        login_fails = session.get('login_fails', {})

        # Check lockout before attempting password (username only, regular users only)
        if not is_email and identifier and user and user.role_level <= 1:
            if login_fails.get(identifier, 0) >= 3:
                return render_template('auth/login.html',
                                       locked_identifier=identifier,
                                       contact_email=_get_contact_email())

        if user and user.check_password(password):
            if not user.is_active:
                flash('Contul tău a fost dezactivat. Contactează un administrator.', 'danger')
                return redirect(url_for('auth.login'))
            login_fails.pop(identifier, None)
            session['login_fails'] = login_fails
            login_user(user, remember=remember)
            flash(f'Bun venit, {user.username}!', 'success')
            return redirect(request.args.get('next') or url_for('main.index'))

        # Wrong password
        if not is_email and identifier:
            login_fails[identifier] = login_fails.get(identifier, 0) + 1
            session['login_fails'] = login_fails
            if user and user.role_level <= 1 and login_fails[identifier] >= 3:
                return render_template('auth/login.html',
                                       locked_identifier=identifier,
                                       contact_email=_get_contact_email())
            remaining = max(0, 3 - login_fails.get(identifier, 0))
            if user and user.role_level <= 1 and remaining > 0:
                flash(f'Parolă incorectă. Mai ai {remaining} '
                      f'{"încercare" if remaining == 1 else "încercări"} cu numele de utilizator.',
                      'warning')
                return render_template('auth/login.html')

        flash('Credențiale incorecte.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        errors = {}
        if not username or len(username) < 3:
            errors['username'] = 'Minim 3 caractere.'
        elif User.query.filter_by(username=username).first():
            errors['username'] = 'Numele de utilizator este deja folosit.'

        if not email or '@' not in email:
            errors['email'] = 'Adresa de email nu este validă.'
        elif User.query.filter_by(email=email).first():
            errors['email'] = 'Adresa de email este deja înregistrată.'

        if len(password) < 3:
            errors['password'] = 'Parola trebuie să aibă minim 3 caractere.'
        elif password != confirm:
            errors['confirm'] = 'Parolele nu se potrivesc.'

        if errors:
            return render_template('auth/register.html', errors=errors,
                                   form_data={'username': username, 'email': email})

        user = User(username=username, email=email, role='user', coins=100)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f'Bun venit, {username}! Cont creat cu succes — ai primit 100 coins cadou!', 'success')
        return redirect(url_for('main.index'))

    return render_template('auth/register.html', errors={}, form_data={})


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Te-ai deconectat cu succes.', 'info')
    return redirect(url_for('main.index'))
