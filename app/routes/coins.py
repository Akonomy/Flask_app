import random
import math
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user
from ..models import db, Coupon, CouponRedemption, GameSettings, User

coins_bp = Blueprint('coins', __name__)


def get_game_settings():
    s = GameSettings.query.first()
    if not s:
        s = GameSettings()
        db.session.add(s)
        db.session.commit()
    return s


# ── Coupon redemption ──────────────────────────────────────────────────────────

@coins_bp.route('/redeem', methods=['GET', 'POST'])
@login_required
def redeem():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        coupon = Coupon.query.filter_by(code=code).first()

        if not coupon or not coupon.is_valid:
            flash('Codul de cupon este invalid sau a expirat.', 'danger')
        else:
            already = CouponRedemption.query.filter_by(
                coupon_id=coupon.id, user_id=current_user.id
            ).first()
            if already:
                flash('Ai folosit deja acest cupon.', 'warning')
            else:
                redemption = CouponRedemption(coupon_id=coupon.id, user_id=current_user.id)
                db.session.add(redemption)
                coupon.used_count += 1
                current_user.add_coins(coupon.coin_value)
                db.session.commit()
                flash(f'Cupon activat! Ai primit {coupon.coin_value} coins.', 'success')
                return redirect(url_for('coins.redeem'))

    return render_template('coins/redeem.html')


# ── Binary search game ─────────────────────────────────────────────────────────

@coins_bp.route('/game')
@login_required
def game():
    game_state = session.get('game')
    settings = get_game_settings()
    return render_template('coins/game.html', game=game_state, settings=settings)


@coins_bp.route('/game/start', methods=['POST'])
@login_required
def game_start():
    settings = get_game_settings()
    target = random.randint(settings.number_min, settings.number_max)
    session['game'] = {
        'target': target,
        'range_min': settings.number_min,
        'range_max': settings.number_max,
        'hint_min': settings.number_min,
        'hint_max': settings.number_max,
        'attempts': 0,
        'max_attempts': settings.max_attempts,
        'history': [],
        'active': True,
        'won': False,
    }
    session.modified = True
    return redirect(url_for('coins.game'))


@coins_bp.route('/game/guess', methods=['POST'])
@login_required
def game_guess():
    game_state = session.get('game')
    if not game_state or not game_state.get('active'):
        return redirect(url_for('coins.game'))

    try:
        guess = int(request.form.get('guess', 0))
    except ValueError:
        flash('Introdu un număr valid.', 'danger')
        return redirect(url_for('coins.game'))

    settings = get_game_settings()
    if guess < settings.number_min or guess > settings.number_max:
        flash(f'Numărul trebuie să fie între {settings.number_min} și {settings.number_max}.', 'warning')
        return redirect(url_for('coins.game'))

    target = game_state['target']
    game_state['attempts'] += 1
    attempt_num = game_state['attempts']

    if guess == target:
        luck = random.uniform(0.85, 1.20)
        base = settings.base_reward
        if attempt_num == 1:
            bonus = settings.bonus_1st
        elif attempt_num == 2:
            bonus = settings.bonus_2nd
        elif attempt_num == 3:
            bonus = settings.bonus_3rd
        else:
            bonus = 0

        reward = max(1, int((base + bonus) * luck))
        current_user.add_coins(reward)
        current_user.games_played = (current_user.games_played or 0) + 1
        current_user.games_won = (current_user.games_won or 0) + 1
        current_user.coins_from_games = (current_user.coins_from_games or 0) + reward
        db.session.commit()

        bonus_msg = f' (bonus {attempt_num}. încercare: +{bonus})' if bonus > 0 else ''
        flash(f'Felicitări! Ai ghicit numărul {target} la încercarea #{attempt_num}! Ai câștigat {reward} coins{bonus_msg}.', 'success')
        session.pop('game', None)

    elif attempt_num >= game_state['max_attempts']:
        if target > guess:
            game_state['history'].append({'guess': guess, 'result': 'mai mare', 'attempt': attempt_num})
        else:
            game_state['history'].append({'guess': guess, 'result': 'mai mic', 'attempt': attempt_num})
        current_user.games_played = (current_user.games_played or 0) + 1
        db.session.commit()
        flash(f'Ai epuizat toate încercările! Numărul era {target}. Mai încearcă!', 'danger')
        session.pop('game', None)

    else:
        if target > guess:
            result = 'mai mare'
            game_state['hint_min'] = max(game_state['hint_min'], guess + 1)
        else:
            result = 'mai mic'
            game_state['hint_max'] = min(game_state['hint_max'], guess - 1)

        game_state['history'].append({'guess': guess, 'result': result, 'attempt': attempt_num})
        session['game'] = game_state

    session.modified = True
    return redirect(url_for('coins.game'))


@coins_bp.route('/game/reset', methods=['POST'])
@login_required
def game_reset():
    session.pop('game', None)
    return redirect(url_for('coins.game'))
