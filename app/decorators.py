from functools import wraps
from flask import abort, flash
from flask_login import current_user
from .models import ROLE_LEVELS


def min_role(role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                from flask import redirect, url_for
                return redirect(url_for('auth.login'))
            if current_user.role_level < ROLE_LEVELS.get(role, 0):
                flash('Nu ai permisiunea să accesezi această pagină.', 'danger')
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator
