from flask import Blueprint, render_template, abort, redirect, url_for, flash, request
from flask_login import login_required, current_user
from ..models import Order, OrderStatusHistory, db
from ..models import utcnow

orders_bp = Blueprint('orders', __name__)


@orders_bp.route('/')
@login_required
def history():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(
        Order.created_at.desc()
    ).all()
    return render_template('orders/history.html', orders=orders)


@orders_bp.route('/<int:order_id>')
@login_required
def detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and current_user.role_level < 2:
        abort(403)
    return render_template('orders/detail.html', order=order)


@orders_bp.route('/<int:order_id>/advance', methods=['POST'])
@login_required
def advance(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and current_user.role_level < 2:
        abort(403)

    next_status = Order.NEXT_STATUS.get(order.status)
    if not next_status:
        flash('Comanda este deja în starea finală.', 'info')
        return redirect(url_for('orders.detail', order_id=order_id))

    note_map = {
        'processing': 'Comanda a intrat în procesare (manual)',
        'shipped': 'Comanda a fost expediată (manual)',
        'delivered': 'Comanda a fost livrată (manual)',
    }

    now = utcnow()
    order.status = next_status
    order.updated_at = now
    order.advance_pending_at = None

    db.session.add(OrderStatusHistory(
        order_id=order.id,
        status=next_status,
        changed_at=now,
        note=note_map.get(next_status, '')
    ))
    db.session.commit()
    flash(f'Statusul comenzii a fost actualizat la: {order.status_display}', 'success')
    return redirect(url_for('orders.detail', order_id=order_id))
