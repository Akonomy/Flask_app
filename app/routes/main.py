from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user, logout_user
from ..models import db, Product, AboutProfile, Order, User, utcnow
from ..decorators import min_role

main_bp = Blueprint('main', __name__)

SOCIAL_PLATFORMS = [
    ('github_url',    'GitHub',    'bi-github',    'github.com'),
    ('linkedin_url',  'LinkedIn',  'bi-linkedin',  'linkedin.com/in'),
    ('instagram_url', 'Instagram', 'bi-instagram', 'instagram.com'),
    ('facebook_url',  'Facebook',  'bi-facebook',  'facebook.com'),
    ('twitter_url',   'Twitter/X', 'bi-twitter-x', 'x.com'),
    ('website_url',   'Website',   'bi-globe',     'site-ul tău'),
    ('youtube_url',   'YouTube',   'bi-youtube',   'youtube.com'),
    ('tiktok_url',    'TikTok',    'bi-tiktok',    'tiktok.com'),
]


@main_bp.route('/')
def index():
    featured = Product.query.filter_by(is_active=True).filter(
        Product.stock > 0
    ).order_by(Product.created_at.desc()).limit(8).all()
    return render_template('index.html', featured=featured)


@main_bp.route('/about')
def about():
    profile = AboutProfile.query.first()
    return render_template('about.html', profile=profile, SOCIAL_PLATFORMS=SOCIAL_PLATFORMS)


@main_bp.route('/about/edit', methods=['GET', 'POST'])
@login_required
@min_role('developer')
def about_edit():
    profile = AboutProfile.query.first()
    if not profile:
        profile = AboutProfile()
        db.session.add(profile)
        db.session.commit()

    if request.method == 'POST':
        profile.full_name = request.form.get('full_name', '').strip()
        profile.faculty = request.form.get('faculty', '').strip()
        profile.university = request.form.get('university', '').strip()
        profile.study_year = request.form.get('study_year', '').strip()
        profile.specialization = request.form.get('specialization', '').strip()
        profile.about_text = request.form.get('about_text', '').strip()
        profile.email = request.form.get('email', '').strip()
        for field, *_ in SOCIAL_PLATFORMS:
            profile.__setattr__(field, request.form.get(field, '').strip())
        db.session.commit()
        flash('Pagina About a fost actualizată.', 'success')
        return redirect(url_for('main.about'))

    return render_template('about_edit.html', profile=profile, SOCIAL_PLATFORMS=SOCIAL_PLATFORMS)


@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    errors = {}
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_email':
            new_email = request.form.get('email', '').strip().lower()
            password = request.form.get('password_check', '')
            if not current_user.check_password(password):
                errors['email_password'] = 'Parola curentă este incorectă.'
            elif not new_email or '@' not in new_email:
                errors['email'] = 'Email invalid.'
            elif User.query.filter(User.email == new_email,
                                   User.id != current_user.id).first():
                errors['email'] = 'Emailul este deja folosit de alt cont.'
            else:
                current_user.email = new_email
                db.session.commit()
                flash('Emailul a fost actualizat cu succes.', 'success')
                return redirect(url_for('main.profile'))

        elif action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            if not current_user.check_password(current_pw):
                errors['current_password'] = 'Parola curentă este incorectă.'
            elif len(new_pw) < 3:
                errors['new_password'] = 'Parola trebuie să aibă minim 3 caractere.'
            elif new_pw != confirm_pw:
                errors['confirm_password'] = 'Parolele nu se potrivesc.'
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash('Parola a fost schimbată cu succes.', 'success')
                return redirect(url_for('main.profile'))

    orders = Order.query.filter_by(user_id=current_user.id).order_by(
        Order.created_at.desc()).limit(5).all()
    win_rate = int(current_user.games_won / current_user.games_played * 100) \
        if (current_user.games_played or 0) > 0 else 0
    return render_template('profile.html', orders=orders, errors=errors,
                           win_rate=win_rate)


@main_bp.route('/account/delete', methods=['POST'])
@login_required
def delete_account():
    password = request.form.get('password', '')
    if not current_user.check_password(password):
        flash('Parola introdusă este incorectă.', 'danger')
        return redirect(url_for('main.profile'))

    role = current_user.role
    current_user.deleted_at = utcnow()
    current_user.is_active = False
    db.session.commit()
    logout_user()

    retention = '24 de ore' if role == 'developer' else '30 de zile'
    flash(f'Contul tău a fost marcat pentru ștergere. Datele vor fi șterse definitiv în {retention}. Un admin îl poate reactiva în acest interval.', 'info')
    return redirect(url_for('main.index'))
