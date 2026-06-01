import os
import uuid
import string
import random
from datetime import datetime, timedelta
from flask import (Blueprint, render_template, redirect, url_for, request,
                   flash, abort, current_app)
from flask_login import login_required, current_user
from sqlalchemy import func
from ..models import (db, Product, User, Order, OrderItem, Coupon, CouponRedemption,
                      GameSettings, OrderStatusHistory, WishlistItem)
from ..decorators import min_role
from ..models import utcnow

panel_bp = Blueprint('panel', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file):
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f'{uuid.uuid4().hex}.{ext}'
        upload_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        file.save(os.path.join(upload_dir, filename))
        return filename
    return None


# ── Dashboard ─────────────────────────────────────────────────────────────────

@panel_bp.route('/')
@login_required
@min_role('manager')
def dashboard():
    total_products = Product.query.filter_by(is_active=True).count()
    total_orders = Order.query.count()
    total_users = User.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()

    low_stock = Product.query.filter(
        Product.stock <= 5, Product.is_active == True
    ).order_by(Product.stock.asc()).all()

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()

    # Orders by status for pie chart
    status_data = db.session.query(
        Order.status, func.count(Order.id)
    ).group_by(Order.status).all()
    status_labels = [r[0] for r in status_data]
    status_counts = [r[1] for r in status_data]

    # Products with lowest stock (top 10)
    low_products = Product.query.filter_by(is_active=True).order_by(
        Product.stock.asc()
    ).limit(10).all()
    stock_names = [p.name[:20] for p in low_products]
    stock_values = [p.stock for p in low_products]

    # Orders last 7 days
    days_labels, days_counts = [], []
    for i in range(6, -1, -1):
        d = datetime.utcnow().date() - timedelta(days=i)
        cnt = Order.query.filter(
            func.date(Order.created_at) == d.isoformat()
        ).count()
        days_labels.append(d.strftime('%d/%m'))
        days_counts.append(cnt)

    return render_template('panel/dashboard.html',
                           total_products=total_products,
                           total_orders=total_orders,
                           total_users=total_users,
                           pending_orders=pending_orders,
                           low_stock=low_stock,
                           recent_orders=recent_orders,
                           status_labels=status_labels,
                           status_counts=status_counts,
                           stock_names=stock_names,
                           stock_values=stock_values,
                           days_labels=days_labels,
                           days_counts=days_counts)


# ── Products ──────────────────────────────────────────────────────────────────

@panel_bp.route('/products')
@login_required
@min_role('manager')
def products():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = Product.query
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    pagination = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('panel/products.html', products=pagination, search=search)


@panel_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@min_role('manager')
def add_product():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = request.form.get('price', '').strip()
        stock = request.form.get('stock', '0').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        is_active = bool(request.form.get('is_active'))

        errors = {}
        if not name:
            errors['name'] = 'Numele produsului este obligatoriu.'
        if not price:
            errors['price'] = 'Prețul este obligatoriu.'
        else:
            try:
                price = int(price)
                if price < 1:
                    errors['price'] = 'Prețul trebuie să fie minim 1.'
            except ValueError:
                errors['price'] = 'Prețul trebuie să fie un număr întreg.'
        try:
            stock = int(stock)
        except ValueError:
            errors['stock'] = 'Stocul trebuie să fie un număr întreg.'
        if errors:
            categories = sorted(set(
                r[0] for r in db.session.query(Product.category)
                .filter(Product.category.isnot(None), Product.category != '').all()
            ))
            return render_template('panel/product_form.html', product=None, action='add',
                                   errors=errors, form_data=request.form, categories=categories)

        image_filename = save_image(request.files.get('image'))
        image_url_external = request.form.get('image_url_external', '').strip() or None
        try:
            weight_g = int(request.form.get('weight_g', 200))
        except ValueError:
            weight_g = 200
        from ..models import CATEGORY_DEFAULT_WEIGHTS
        if not request.form.get('weight_g', '').strip():
            weight_g = CATEGORY_DEFAULT_WEIGHTS.get(category, 200)

        product = Product(
            name=name, price=price, stock=stock,
            category=category or None,
            description=description or None,
            image_filename=image_filename,
            image_url_external=image_url_external,
            weight_g=weight_g,
            is_active=is_active,
            created_by_id=current_user.id
        )
        db.session.add(product)
        db.session.commit()
        flash(f'Produsul "{name}" a fost adăugat.', 'success')
        return redirect(url_for('panel.products'))

    categories = sorted(set(
        r[0] for r in db.session.query(Product.category)
        .filter(Product.category.isnot(None), Product.category != '').all()
    ))
    return render_template('panel/product_form.html', product=None, action='add',
                           categories=categories)


@panel_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@min_role('manager')
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form.get('name', '').strip()
        price_str = request.form.get('price', '').strip()
        stock_str = request.form.get('stock', '0').strip()
        product.category = request.form.get('category', '').strip() or None
        product.description = request.form.get('description', '').strip() or None
        product.is_active = bool(request.form.get('is_active'))

        errors = {}
        if not product.name:
            errors['name'] = 'Numele produsului este obligatoriu.'
        if not price_str:
            errors['price'] = 'Prețul este obligatoriu.'
        else:
            try:
                product.price = int(price_str)
                if product.price < 1:
                    errors['price'] = 'Prețul trebuie să fie minim 1.'
            except ValueError:
                errors['price'] = 'Prețul trebuie să fie un număr întreg.'
        try:
            product.stock = int(stock_str)
        except ValueError:
            errors['stock'] = 'Stocul trebuie să fie un număr întreg.'
        if errors:
            categories = sorted(set(
                r[0] for r in db.session.query(Product.category)
                .filter(Product.category.isnot(None), Product.category != '').all()
            ))
            return render_template('panel/product_form.html', product=product, action='edit',
                                   errors=errors, form_data=None, categories=categories)

        new_image = save_image(request.files.get('image'))
        if new_image:
            if product.image_filename:
                old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], product.image_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            product.image_filename = new_image

        ext_url = request.form.get('image_url_external', '').strip()
        product.image_url_external = ext_url or None

        try:
            product.weight_g = int(request.form.get('weight_g', 200))
        except ValueError:
            product.weight_g = 200

        db.session.commit()
        flash(f'Produsul "{product.name}" a fost actualizat.', 'success')
        return redirect(url_for('panel.products'))

    categories = sorted(set(
        r[0] for r in db.session.query(Product.category)
        .filter(Product.category.isnot(None), Product.category != '').all()
    ))
    return render_template('panel/product_form.html', product=product, action='edit',
                           categories=categories)


@panel_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
@min_role('manager')
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = False
    db.session.commit()
    flash(f'Produsul "{product.name}" a fost dezactivat.', 'info')
    return redirect(url_for('panel.products'))


@panel_bp.route('/products/<int:product_id>/toggle', methods=['POST'])
@login_required
@min_role('manager')
def toggle_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    state = 'activat' if product.is_active else 'dezactivat'
    flash(f'Produsul "{product.name}" a fost {state}.', 'info')
    return redirect(url_for('panel.products'))


# ── Orders ────────────────────────────────────────────────────────────────────

@panel_bp.route('/orders')
@login_required
@min_role('manager')
def orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '').strip()
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('panel/orders.html', orders=pagination,
                           status_filter=status_filter,
                           statuses=list(Order.STATUS_LABELS.keys()))


@panel_bp.route('/orders/<int:order_id>')
@login_required
@min_role('manager')
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('panel/order_detail.html', order=order,
                           statuses=list(Order.STATUS_LABELS.keys()))


@panel_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@login_required
@min_role('manager')
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status', '').strip()
    tracking_notes = request.form.get('tracking_notes', '').strip()
    if new_status not in Order.STATUS_LABELS:
        flash('Status invalid.', 'danger')
    else:
        now = utcnow()
        order.status = new_status
        order.updated_at = now
        order.advance_pending_at = None
        if tracking_notes:
            order.tracking_notes = tracking_notes
        db.session.add(OrderStatusHistory(
            order_id=order.id, status=new_status, changed_at=now,
            note=f'Actualizat manual de {current_user.username}'
        ))
        db.session.commit()
        flash('Statusul comenzii a fost actualizat.', 'success')
    return redirect(url_for('panel.order_detail', order_id=order_id))


# ── Users (admin+) ────────────────────────────────────────────────────────────

@panel_bp.route('/users')
@login_required
@min_role('admin')
def users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) | (User.email.ilike(f'%{search}%'))
        )
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('panel/users.html', users=pagination, search=search)


@panel_bp.route('/users/<int:user_id>')
@login_required
@min_role('admin')
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    orders = Order.query.filter_by(user_id=user_id).order_by(
        Order.created_at.desc()).limit(10).all()
    coupons = Coupon.query.filter_by(is_active=True).all()
    return render_template('panel/user_detail.html', user=user,
                           orders=orders, coupons=coupons,
                           roles=['user', 'manager', 'admin', 'developer'])


@panel_bp.route('/users/<int:user_id>/coins', methods=['POST'])
@login_required
@min_role('admin')
def user_coins(user_id):
    user = User.query.get_or_404(user_id)
    action = request.form.get('action')
    try:
        amount = int(request.form.get('amount', 0))
    except ValueError:
        flash('Sumă invalidă.', 'danger')
        return redirect(url_for('panel.user_detail', user_id=user_id))

    if action == 'add':
        user.add_coins(amount)
        flash(f'Au fost adăugați {amount} coins utilizatorului {user.username}.', 'success')
    elif action == 'remove':
        user.coins = max(0, user.coins - amount)
        flash(f'Au fost eliminați {amount} coins de la {user.username}.', 'info')
    db.session.commit()
    return redirect(url_for('panel.user_detail', user_id=user_id))


@panel_bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
@min_role('admin')
def user_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Nu îți poți modifica propriul rol.', 'warning')
        return redirect(url_for('panel.user_detail', user_id=user_id))
    new_role = request.form.get('role', 'user')
    if new_role not in ['user', 'manager', 'admin', 'developer']:
        flash('Rol invalid.', 'danger')
    elif current_user.role == 'developer':
        user.role = new_role
        db.session.commit()
        flash(f'Rolul lui {user.username} a fost schimbat în {new_role}.', 'success')
    elif user.role == 'developer':
        flash('Doar developer-ul poate modifica rolul unui alt developer.', 'danger')
    elif new_role == 'developer':
        flash('Doar developer-ul poate acorda rol de developer.', 'danger')
    else:
        user.role = new_role
        db.session.commit()
        flash(f'Rolul lui {user.username} a fost schimbat în {new_role}.', 'success')
    return redirect(url_for('panel.user_detail', user_id=user_id))


@panel_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@min_role('admin')
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Nu îți poți dezactiva propriul cont.', 'warning')
        return redirect(url_for('panel.user_detail', user_id=user_id))
    user.is_active = not user.is_active
    db.session.commit()
    state = 'activat' if user.is_active else 'dezactivat'
    flash(f'Contul {user.username} a fost {state}.', 'info')
    return redirect(url_for('panel.user_detail', user_id=user_id))


@panel_bp.route('/users/<int:user_id>/give-coupon', methods=['POST'])
@login_required
@min_role('admin')
def give_coupon_to_user(user_id):
    user = User.query.get_or_404(user_id)
    coupon_id = request.form.get('coupon_id', type=int)
    coupon = Coupon.query.get(coupon_id)
    if not coupon or not coupon.is_valid:
        flash('Cuponul selectat nu este valid.', 'danger')
    else:
        already = CouponRedemption.query.filter_by(
            coupon_id=coupon.id, user_id=user.id).first()
        if already:
            flash(f'{user.username} a folosit deja acest cupon.', 'warning')
        else:
            r = CouponRedemption(coupon_id=coupon.id, user_id=user.id)
            db.session.add(r)
            coupon.used_count += 1
            user.add_coins(coupon.coin_value)
            db.session.commit()
            flash(f'Cuponul a fost aplicat. {user.username} a primit {coupon.coin_value} coins.', 'success')
    return redirect(url_for('panel.user_detail', user_id=user_id))


@panel_bp.route('/users/<int:user_id>/developer-settings', methods=['POST'])
@login_required
@min_role('developer')
def developer_settings(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != 'developer':
        flash('Utilizatorul nu are rol de developer.', 'danger')
        return redirect(url_for('panel.user_detail', user_id=user_id))
    unlimited = bool(request.form.get('unlimited'))
    user.developer_unlimited = unlimited
    if not unlimited:
        try:
            user.developer_coin_limit = int(request.form.get('coin_limit', 0))
        except ValueError:
            user.developer_coin_limit = None
    else:
        user.developer_coin_limit = None
    db.session.commit()
    flash('Setările developer au fost actualizate.', 'success')
    return redirect(url_for('panel.user_detail', user_id=user_id))


# ── Coupons (admin+) ──────────────────────────────────────────────────────────

def _generate_code(length=10):
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=length))
        if not Coupon.query.filter_by(code=code).first():
            return code


@panel_bp.route('/coupons')
@login_required
@min_role('admin')
def coupons():
    page = request.args.get('page', 1, type=int)
    pagination = Coupon.query.order_by(Coupon.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('panel/coupons.html', coupons=pagination)


@panel_bp.route('/coupons/add', methods=['GET', 'POST'])
@login_required
@min_role('admin')
def add_coupon():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        if not code:
            code = _generate_code()
        try:
            coin_value = int(request.form.get('coin_value', 0))
            max_uses = int(request.form.get('max_uses', 1))
            days_valid = int(request.form.get('days_valid', 30))
        except ValueError:
            flash('Valori numerice invalide.', 'danger')
            return render_template('panel/coupon_form.html')

        if Coupon.query.filter_by(code=code).first():
            flash('Codul există deja. Alege alt cod sau lasă gol pentru generare automată.', 'danger')
            return render_template('panel/coupon_form.html')

        expiry = datetime.utcnow() + timedelta(days=days_valid)
        coupon = Coupon(code=code, coin_value=coin_value, max_uses=max_uses,
                        expiry_date=expiry, created_by_id=current_user.id)
        db.session.add(coupon)
        db.session.commit()
        flash(f'Cuponul {code} a fost creat (valoare: {coin_value} coins, {max_uses} utilizări).', 'success')
        return redirect(url_for('panel.coupons'))

    return render_template('panel/coupon_form.html', generated_code=_generate_code())


@panel_bp.route('/coupons/<int:coupon_id>/deactivate', methods=['POST'])
@login_required
@min_role('admin')
def deactivate_coupon(coupon_id):
    coupon = Coupon.query.get_or_404(coupon_id)
    coupon.is_active = False
    db.session.commit()
    flash(f'Cuponul {coupon.code} a fost dezactivat.', 'info')
    return redirect(url_for('panel.coupons'))


# ── Settings (admin+) ─────────────────────────────────────────────────────────

@panel_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@min_role('admin')
def settings():
    gs = GameSettings.query.first()
    if request.method == 'POST':
        try:
            gs.base_reward = int(request.form.get('base_reward', 50))
            gs.bonus_1st = int(request.form.get('bonus_1st', 500))
            gs.bonus_2nd = int(request.form.get('bonus_2nd', 200))
            gs.bonus_3rd = int(request.form.get('bonus_3rd', 50))
            gs.number_min = int(request.form.get('number_min', 1))
            gs.number_max = int(request.form.get('number_max', 5000))
            gs.attempts_buffer = int(request.form.get('attempts_buffer', 3))
            db.session.commit()
            flash('Setările jocului au fost salvate.', 'success')
        except ValueError:
            flash('Valori invalide.', 'danger')
        return redirect(url_for('panel.settings'))

    return render_template('panel/settings.html', gs=gs)


# ── Account reactivation (admin+) ─────────────────────────────────────────────

@panel_bp.route('/users/<int:user_id>/reactivate', methods=['POST'])
@login_required
@min_role('admin')
def reactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    if not user.deleted_at:
        flash('Contul nu este marcat pentru ștergere.', 'warning')
        return redirect(url_for('panel.user_detail', user_id=user_id))
    user.deleted_at = None
    user.is_active = True
    db.session.commit()
    flash(f'Contul "{user.username}" a fost reactivat.', 'success')
    return redirect(url_for('panel.user_detail', user_id=user_id))


# ── Wishlist view (manager+) ───────────────────────────────────────────────────

@panel_bp.route('/wishlist')
@login_required
@min_role('manager')
def wishlist():
    from sqlalchemy import func
    rows = db.session.query(
        WishlistItem.product_id,
        func.count(WishlistItem.id).label('count')
    ).group_by(WishlistItem.product_id).order_by(func.count(WishlistItem.id).desc()).all()

    product_ids = [r.product_id for r in rows]
    counts = {r.product_id: r.count for r in rows}
    products = Product.query.filter(Product.id.in_(product_ids)).all() if product_ids else []
    products_map = {p.id: p for p in products}

    items = []
    for pid in product_ids:
        p = products_map.get(pid)
        if p:
            items.append({'product': p, 'count': counts[pid]})

    return render_template('panel/wishlist.html', items=items)
