import random
from datetime import timedelta, timezone, datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import login_required, current_user
from ..models import db, Product, Order, OrderItem, OrderStatusHistory, WishlistItem
from ..models import utcnow

shop_bp = Blueprint('shop', __name__)

DELIVERY_COST = 15
EXPRESS_SURCHARGE = 10


def get_cart():
    return session.get('cart', {})


def save_cart(cart):
    session['cart'] = cart
    session.modified = True


@shop_bp.route('/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    if not product.is_active or product.stock <= 0:
        flash('Produsul nu este disponibil.', 'danger')
        return redirect(request.referrer or url_for('products.list_products'))

    cart = get_cart()
    qty = int(request.form.get('quantity', 1))
    key = str(product_id)

    current_qty = cart.get(key, {}).get('quantity', 0)
    new_qty = current_qty + qty
    if new_qty > product.stock:
        flash(f'Stoc insuficient. Disponibil: {product.stock}.', 'warning')
        new_qty = product.stock

    cart[key] = {
        'quantity': new_qty,
        'name': product.name,
        'price': product.price,
        'image': product.image_filename or product.image_url_external
    }
    save_cart(cart)
    flash(f'"{product.name}" a fost adăugat în coș!', 'success')
    return redirect(request.referrer or url_for('products.list_products'))


@shop_bp.route('/wishlist/toggle/<int:product_id>', methods=['POST'])
@login_required
def toggle_wishlist(product_id):
    existing = WishlistItem.query.filter_by(
        user_id=current_user.id, product_id=product_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'wishlisted': False})
    db.session.add(WishlistItem(user_id=current_user.id, product_id=product_id))
    db.session.commit()
    return jsonify({'wishlisted': True})


@shop_bp.route('/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    save_cart(cart)
    return redirect(url_for('shop.cart'))


@shop_bp.route('/update/<int:product_id>', methods=['POST'])
@login_required
def update_cart(product_id):
    qty = int(request.form.get('quantity', 1))
    cart = get_cart()
    key = str(product_id)
    if qty <= 0:
        cart.pop(key, None)
    elif key in cart:
        product = Product.query.get(product_id)
        if product:
            cart[key]['quantity'] = min(qty, product.stock)
    save_cart(cart)
    return redirect(url_for('shop.cart'))


@shop_bp.route('/cart')
@login_required
def cart():
    cart = get_cart()
    subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('shop/cart.html', cart=cart, subtotal=subtotal,
                           delivery_cost=DELIVERY_COST, express_surcharge=EXPRESS_SURCHARGE)


@shop_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = get_cart()
    if not cart:
        flash('Coșul tău este gol.', 'warning')
        return redirect(url_for('products.list_products'))

    subtotal = sum(item['price'] * item['quantity'] for item in cart.values())

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        phone = request.form.get('phone', '').strip()
        is_express = bool(request.form.get('express'))

        delivery_cost = DELIVERY_COST + (EXPRESS_SURCHARGE if is_express else 0)
        grand_total = subtotal + delivery_cost

        if not all([name, address, city, phone]):
            flash('Completează toate câmpurile obligatorii.', 'danger')
            return render_template('shop/checkout.html', cart=cart, subtotal=subtotal,
                                   delivery_cost=delivery_cost, is_express=is_express,
                                   express_surcharge=EXPRESS_SURCHARGE)

        if not current_user.can_afford(grand_total):
            flash(f'Coins insuficienți. Ai {current_user.display_coins} coins, necesari {grand_total}.', 'danger')
            return render_template('shop/checkout.html', cart=cart, subtotal=subtotal,
                                   delivery_cost=delivery_cost, is_express=is_express,
                                   express_surcharge=EXPRESS_SURCHARGE)

        for pid, item in cart.items():
            product = Product.query.get(int(pid))
            if not product or not product.is_active or product.stock < item['quantity']:
                flash(f'Produsul "{item["name"]}" nu mai este disponibil în cantitatea dorită.', 'danger')
                return render_template('shop/checkout.html', cart=cart, subtotal=subtotal,
                                       delivery_cost=delivery_cost, is_express=is_express,
                                       express_surcharge=EXPRESS_SURCHARGE)

        now = utcnow()
        first_delay = random.randint(30, 60) if is_express else random.randint(60, 120)
        total_delivery_secs = 3 * (45 if is_express else 90)

        order = Order(
            user_id=current_user.id,
            total_coins=subtotal,
            delivery_cost=delivery_cost,
            is_express=is_express,
            delivery_name=name,
            delivery_address=address,
            delivery_city=city,
            delivery_phone=phone,
            status='pending',
            advance_pending_at=now + timedelta(seconds=first_delay),
            estimated_delivery_at=now + timedelta(seconds=total_delivery_secs)
        )
        db.session.add(order)
        db.session.flush()

        db.session.add(OrderStatusHistory(
            order_id=order.id,
            status='pending',
            changed_at=now,
            note='Comandă plasată'
        ))

        for pid, item in cart.items():
            product = Product.query.get(int(pid))
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item['quantity'],
                price_at_purchase=item['price']
            )
            product.stock -= item['quantity']
            db.session.add(order_item)

        current_user.deduct_coins(grand_total)
        db.session.commit()
        save_cart({})
        flash(f'Comanda #{order.id} a fost plasată cu succes!', 'success')
        return redirect(url_for('orders.detail', order_id=order.id))

    return render_template('shop/checkout.html', cart=cart, subtotal=subtotal,
                           delivery_cost=DELIVERY_COST, is_express=False,
                           express_surcharge=EXPRESS_SURCHARGE)
