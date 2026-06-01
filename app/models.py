from datetime import datetime, timezone
import math
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

ROLE_LEVELS = {'user': 1, 'manager': 2, 'admin': 3, 'developer': 4}

CATEGORY_DEFAULT_WEIGHTS = {
    'Îngrijire personală': 300,
    'Tehnologie': 500,
    'Îmbrăcăminte': 400,
    'Librărie': 600,
    'Sport': 800,
    'Filme': 150,
    'Gaming': 80,
}


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)
    coins = db.Column(db.Integer, default=0, nullable=False)
    developer_unlimited = db.Column(db.Boolean, default=False)
    developer_coin_limit = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    is_active = db.Column(db.Boolean, default=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    games_played = db.Column(db.Integer, default=0)
    games_won = db.Column(db.Integer, default=0)
    coins_from_games = db.Column(db.Integer, default=0)

    orders = db.relationship('Order', backref='user', lazy=True)
    coupon_redemptions = db.relationship('CouponRedemption', backref='user', lazy=True)
    wishlist_items = db.relationship('WishlistItem', backref='user', lazy=True,
                                     cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def role_level(self):
        return ROLE_LEVELS.get(self.role, 0)

    @property
    def has_unlimited_coins(self):
        return self.role == 'developer' and self.developer_unlimited

    @property
    def display_coins(self):
        if self.has_unlimited_coins:
            return '∞'
        return self.coins

    def can_afford(self, amount):
        if self.has_unlimited_coins:
            return True
        return self.coins >= amount

    def deduct_coins(self, amount):
        if not self.has_unlimited_coins:
            self.coins = max(0, self.coins - amount)

    def add_coins(self, amount):
        self.coins += amount
        if self.role == 'developer' and self.developer_coin_limit is not None:
            self.coins = min(self.coins, self.developer_coin_limit)

    @property
    def total_orders(self):
        return Order.query.filter_by(user_id=self.id).count()

    @property
    def is_pending_deletion(self):
        return self.deleted_at is not None

    @property
    def deletion_retention_hours(self):
        return 24 if self.role == 'developer' else 30 * 24

    def __repr__(self):
        return f'<User {self.username}>'


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)
    image_url_external = db.Column(db.String(1000), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    stock = db.Column(db.Integer, default=0, nullable=False)
    weight_g = db.Column(db.Integer, default=200)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    wishlist_items = db.relationship('WishlistItem', backref='product', lazy=True,
                                     cascade='all, delete-orphan')

    @property
    def image_url(self):
        if self.image_filename:
            return f'/static/uploads/products/{self.image_filename}'
        if self.image_url_external:
            return self.image_url_external
        return None

    @property
    def is_low_stock(self):
        return self.stock <= 5

    def __repr__(self):
        return f'<Product {self.name}>'


class Order(db.Model):
    __tablename__ = 'orders'

    STATUS_LABELS = {
        'pending': ('În așteptare', 'warning'),
        'processing': ('În procesare', 'info'),
        'shipped': ('Expediat', 'primary'),
        'delivered': ('Livrat', 'success'),
        'cancelled': ('Anulat', 'danger'),
    }

    NEXT_STATUS = {
        'pending': 'processing',
        'processing': 'shipped',
        'shipped': 'delivered',
    }

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False)
    total_coins = db.Column(db.Integer, nullable=False)
    delivery_cost = db.Column(db.Integer, default=15)
    is_express = db.Column(db.Boolean, default=False)
    advance_pending_at = db.Column(db.DateTime, nullable=True)
    estimated_delivery_at = db.Column(db.DateTime, nullable=True)
    delivery_name = db.Column(db.String(200), nullable=False)
    delivery_address = db.Column(db.String(500), nullable=False)
    delivery_city = db.Column(db.String(100), nullable=False)
    delivery_phone = db.Column(db.String(20), nullable=False)
    tracking_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow)

    items = db.relationship('OrderItem', backref='order', lazy=True,
                            cascade='all, delete-orphan')
    status_history = db.relationship('OrderStatusHistory', backref='order', lazy=True,
                                     cascade='all, delete-orphan',
                                     order_by='OrderStatusHistory.changed_at')

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, ('Necunoscut', 'secondary'))

    @property
    def status_display(self):
        return self.STATUS_LABELS.get(self.status, ('Necunoscut', 'secondary'))[0]

    @property
    def status_color(self):
        return self.STATUS_LABELS.get(self.status, ('Necunoscut', 'secondary'))[1]

    @property
    def grand_total(self):
        return self.total_coins + (self.delivery_cost or 15)

    def __repr__(self):
        return f'<Order #{self.id}>'


class OrderStatusHistory(db.Model):
    __tablename__ = 'order_status_history'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    changed_at = db.Column(db.DateTime, default=utcnow)
    note = db.Column(db.String(300), nullable=True)


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price_at_purchase = db.Column(db.Integer, nullable=False)

    @property
    def subtotal(self):
        return self.quantity * self.price_at_purchase


class WishlistItem(db.Model):
    __tablename__ = 'wishlist_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=utcnow)


class Coupon(db.Model):
    __tablename__ = 'coupons'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    coin_value = db.Column(db.Integer, nullable=False)
    max_uses = db.Column(db.Integer, nullable=False)
    used_count = db.Column(db.Integer, default=0)
    expiry_date = db.Column(db.DateTime, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    is_active = db.Column(db.Boolean, default=True)

    redemptions = db.relationship('CouponRedemption', backref='coupon', lazy=True)

    @property
    def is_valid(self):
        return (
            self.is_active and
            self.used_count < self.max_uses and
            self.expiry_date > datetime.utcnow()
        )

    @property
    def remaining_uses(self):
        return self.max_uses - self.used_count

    def __repr__(self):
        return f'<Coupon {self.code}>'


class CouponRedemption(db.Model):
    __tablename__ = 'coupon_redemptions'

    id = db.Column(db.Integer, primary_key=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupons.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    redeemed_at = db.Column(db.DateTime, default=utcnow)


class GameSettings(db.Model):
    __tablename__ = 'game_settings'

    id = db.Column(db.Integer, primary_key=True)
    base_reward = db.Column(db.Integer, default=50)
    bonus_1st = db.Column(db.Integer, default=500)
    bonus_2nd = db.Column(db.Integer, default=200)
    bonus_3rd = db.Column(db.Integer, default=50)
    number_min = db.Column(db.Integer, default=1)
    number_max = db.Column(db.Integer, default=5000)
    attempts_buffer = db.Column(db.Integer, default=3)

    @property
    def optimal_attempts(self):
        rng = self.number_max - self.number_min + 1
        return math.ceil(math.log2(max(rng, 2)))

    @property
    def max_attempts(self):
        return self.optimal_attempts + self.attempts_buffer


class AboutProfile(db.Model):
    __tablename__ = 'about_profile'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), default='Prenume Nume')
    faculty = db.Column(db.String(300), default='Facultatea de Automatică și Calculatoare')
    university = db.Column(db.String(300), default='Universitatea Tehnică')
    study_year = db.Column(db.String(50), default='Anul II')
    specialization = db.Column(db.String(200), default='Calculatoare și IT')
    about_text = db.Column(db.Text, default='Sunt student pasionat de programare și tehnologie. Îmi place să construiesc aplicații web și să rezolv probleme complexe.')
    email = db.Column(db.String(200), default='student@example.com')
    github_url = db.Column(db.String(500), default='')
    linkedin_url = db.Column(db.String(500), default='')
    instagram_url = db.Column(db.String(500), default='')
    facebook_url = db.Column(db.String(500), default='')
    twitter_url = db.Column(db.String(500), default='')
    website_url = db.Column(db.String(500), default='')
    youtube_url = db.Column(db.String(500), default='')
    tiktok_url = db.Column(db.String(500), default='')
