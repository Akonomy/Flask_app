import os
import threading
import random
from datetime import timedelta, timezone, datetime
from flask import Flask, render_template, session
from .config import Config
from .extensions import db, login_manager

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    _BUCHAREST = ZoneInfo('Europe/Bucharest')
except Exception:
    _BUCHAREST = timezone(timedelta(hours=3))


def _ro_time(dt):
    if dt is None:
        return ''
    if isinstance(dt, datetime) and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(_BUCHAREST)
    return local.strftime('%d.%m.%Y %H:%M')


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    app.jinja_env.filters['ro_time'] = _ro_time

    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.products import products_bp
    from .routes.shop import shop_bp
    from .routes.orders import orders_bp
    from .routes.coins import coins_bp
    from .routes.panel import panel_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(shop_bp, url_prefix='/shop')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(coins_bp, url_prefix='/coins')
    app.register_blueprint(panel_bp, url_prefix='/panel')

    @app.context_processor
    def inject_globals():
        cart = session.get('cart', {})
        cart_count = sum(item['quantity'] for item in cart.values())
        return {'cart_count': cart_count, 'now': datetime.utcnow}

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    with app.app_context():
        db.create_all()
        _run_migrations()
        _init_default_data()

    _start_background_tasks(app)

    return app


def _run_migrations():
    """Add new columns to existing tables without dropping data."""
    from sqlalchemy import text
    conn = db.engine.connect()

    def _add_col(table, col, definition):
        try:
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {definition}'))
            conn.commit()
        except Exception:
            pass

    _add_col('users', 'deleted_at', 'DATETIME')
    _add_col('products', 'image_url_external', 'VARCHAR(1000)')
    _add_col('products', 'weight_g', 'INTEGER DEFAULT 200')
    _add_col('orders', 'delivery_cost', 'INTEGER DEFAULT 15')
    _add_col('orders', 'is_express', 'BOOLEAN DEFAULT 0')
    _add_col('orders', 'advance_pending_at', 'DATETIME')
    _add_col('orders', 'estimated_delivery_at', 'DATETIME')
    _add_col('about_profile', 'instagram_url', 'VARCHAR(500) DEFAULT ""')
    _add_col('about_profile', 'facebook_url', 'VARCHAR(500) DEFAULT ""')
    _add_col('about_profile', 'twitter_url', 'VARCHAR(500) DEFAULT ""')
    _add_col('about_profile', 'website_url', 'VARCHAR(500) DEFAULT ""')
    _add_col('about_profile', 'youtube_url', 'VARCHAR(500) DEFAULT ""')
    _add_col('about_profile', 'tiktok_url', 'VARCHAR(500) DEFAULT ""')

    conn.close()


def _start_background_tasks(app):
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return
    _schedule_advance(app)


def _schedule_advance(app):
    t = threading.Timer(20, _run_advance, args=[app])
    t.daemon = True
    t.start()


def _run_advance(app):
    try:
        with app.app_context():
            _advance_orders()
            _cleanup_deleted_accounts()
    except Exception:
        pass
    _schedule_advance(app)


def _advance_orders():
    from .models import db, Order, OrderStatusHistory
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    orders = Order.query.filter(
        Order.advance_pending_at.isnot(None),
        Order.advance_pending_at <= now,
        Order.status.in_(['pending', 'processing', 'shipped'])
    ).all()

    note_map = {
        'processing': 'Comanda a intrat în procesare',
        'shipped': 'Comanda a fost expediată',
        'delivered': 'Comanda a fost livrată',
    }

    for order in orders:
        next_status = Order.NEXT_STATUS.get(order.status)
        if not next_status:
            continue
        order.status = next_status
        order.updated_at = now
        order.advance_pending_at = None

        db.session.add(OrderStatusHistory(
            order_id=order.id,
            status=next_status,
            changed_at=now,
            note=note_map.get(next_status, '')
        ))

        if next_status != 'delivered':
            delay = random.randint(30, 60) if order.is_express else random.randint(60, 120)
            order.advance_pending_at = now + timedelta(seconds=delay)

    if orders:
        db.session.commit()


def _cleanup_deleted_accounts():
    from .models import db, User
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    expired = User.query.filter(User.deleted_at.isnot(None)).all()
    for user in expired:
        retention_secs = user.deletion_retention_hours * 3600
        if (now - user.deleted_at).total_seconds() >= retention_secs:
            db.session.delete(user)

    if expired:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


def _init_default_data():
    from .models import User, GameSettings, AboutProfile

    if User.query.count() == 0:
        dev = User(username='developer', email='dev@shop.local', role='developer',
                   coins=999999, developer_unlimited=True)
        dev.set_password('dev123')
        admin = User(username='admin', email='admin@shop.local', role='admin', coins=5000)
        admin.set_password('admin123')
        manager = User(username='manager', email='manager@shop.local', role='manager', coins=500)
        manager.set_password('manager123')
        db.session.add_all([dev, admin, manager])

    if GameSettings.query.count() == 0:
        db.session.add(GameSettings())

    if AboutProfile.query.count() == 0:
        db.session.add(AboutProfile())

    db.session.commit()
    _init_sample_products()


def _init_sample_products():
    from .models import Product, db
    if Product.query.count() > 0:
        _update_product_images()
        return

    items = [
        # (name, price, category, description, stock, weight_g, image_url)
        ('Șampon Dove Intense Repair 400ml', 150, 'Îngrijire personală',
         'Șampon cu keratinizare activă pentru păr deteriorat. Redă strălucirea și hidratează intens.', 45, 400,
         'https://picsum.photos/seed/shampoo42/300/200'),
        ('Cremă hidratantă Nivea Q10 Energy 50ml', 220, 'Îngrijire personală',
         'Cremă anti-îmbătrânire cu Q10 și vitamina C. Reduce vizibil ridurile în 4 săptămâni.', 30, 100,
         'https://picsum.photos/seed/cream99/300/200'),
        ('Deodorant Rexona Men Extreme 150ml', 95, 'Îngrijire personală',
         'Protecție antiperspirantă 48h cu tehnologie MotionSense. Rezistent la transpirație intensă.', 60, 150,
         'https://picsum.photos/seed/deodor77/300/200'),
        ('Pastă de dinți Colgate Whitening 75ml', 70, 'Îngrijire personală',
         'Formulă avansată pentru dinți mai albi în 2 săptămâni. Conține fluor activ.', 80, 120,
         'https://picsum.photos/seed/tooth55/300/200'),
        ('Gel de duș Fa Aqua Royal 400ml', 110, 'Îngrijire personală',
         'Gel de duș răcoritor cu extract de alge marine și minerale din ocean.', 50, 420,
         'https://picsum.photos/seed/shower33/300/200'),
        ('Căști Wireless Bluetooth Sony WH-CH520', 1400, 'Tehnologie',
         'Căști over-ear cu Bluetooth 5.2, autonomie 50h, microfon integrat și sunet 360° Reality Audio.', 15, 250,
         'https://picsum.photos/seed/headph10/300/200'),
        ('Mouse Gaming Logitech G102 LIGHTSYNC', 750, 'Tehnologie',
         'Mouse optic gaming 8000 DPI cu iluminare RGB personalizabilă, 6 butoane programabile.', 20, 95,
         'https://picsum.photos/seed/mouse21/300/200'),
        ('Tastatură Mecanică Redragon K552', 1200, 'Tehnologie',
         'Tastatură TKL mecanică cu switch-uri Red, retroiluminare RGB 9 moduri și construcție din aluminiu.', 12, 680,
         'https://picsum.photos/seed/keyb34/300/200'),
        ('Hub USB-C 7 în 1 Multiport', 550, 'Tehnologie',
         'Extinde laptopul cu 3× USB-A 3.0, HDMI 4K, USB-C PD 100W, cititor SD/MicroSD.', 25, 120,
         'https://picsum.photos/seed/usbhub56/300/200'),
        ('Set Cabluri USB-C Fast Charge 65W (2 buc)', 140, 'Tehnologie',
         'Cabluri braided 1m compatibile cu toate dispozitivele USB-C. Suportă 65W și 480Mbps.', 55, 80,
         'https://picsum.photos/seed/cable78/300/200'),
        ('Webcam Full HD 1080p 30fps', 680, 'Tehnologie',
         'Webcam plug & play cu microfon stereo, câmp vizual 90° și corectare automată a luminii.', 18, 180,
         'https://picsum.photos/seed/webcam90/300/200'),
        ('Tricou Bumbac Organic Premium Unisex', 280, 'Îmbrăcăminte',
         'Tricou din 100% bumbac organic GOTS certificat. Croială relaxed-fit, disponibil în 8 culori.', 40, 200,
         'https://picsum.photos/seed/tshirt11/300/200'),
        ('Hanorac Oversize cu Glugă și Fermoar', 620, 'Îmbrăcăminte',
         'Hanorac din fleece 320g/m², talie elastică, buzunare laterale adânci.', 22, 600,
         'https://picsum.photos/seed/hoodie22/300/200'),
        ('Pantaloni Sport Jogger Slim-Fit', 450, 'Îmbrăcăminte',
         'Pantaloni din jerseu tehnic 4-way stretch, șnur reglabil, buzunare cu fermoar.', 28, 350,
         'https://picsum.photos/seed/pants33/300/200'),
        ('Șosete Sport Bumbac (5 perechi)', 130, 'Îmbrăcăminte',
         'Set 5 perechi șosete cu talpă termoformată și arc de sprijin. Talie unisex 39-45.', 70, 150,
         'https://picsum.photos/seed/socks44/300/200'),
        ('Căciulă Lână Merino Ribbed', 220, 'Îmbrăcăminte',
         'Căciulă din lână merino 100%, efect rib knit, extra moale și caldă.', 35, 100,
         'https://picsum.photos/seed/hat55/300/200'),
        ('Clean Code — Robert C. Martin', 420, 'Librărie',
         'Cartea de referință pentru orice programator. Principii și practici pentru cod lizibil.', 15, 500,
         'https://picsum.photos/seed/book101/300/200'),
        ('The Pragmatic Programmer — Hunt & Thomas', 480, 'Librărie',
         'Clasic absolut al literaturii tehnice. 20 de ani de sfaturi practice pentru programatori.', 12, 480,
         'https://picsum.photos/seed/book202/300/200'),
        ('Gândire Rapidă, Gândire Lentă — Kahneman', 350, 'Librărie',
         'Premiul Nobel explică cele două sisteme de gândire ale creierului uman.', 20, 420,
         'https://picsum.photos/seed/book303/300/200'),
        ('Caiet Tehnic A4 200 file Dictando', 90, 'Librărie',
         'Caiet cu hârtie de 80g/m², liniatură dictando, copertă rigidă și elastic de închidere.', 100, 600,
         'https://picsum.photos/seed/noteb44/300/200'),
        ('Set Markere Faber-Castell 24 culori', 180, 'Librărie',
         'Set markere cu vârf dublu (fin 0.4mm + lat 5mm), cerneală pe bază de apă.', 60, 300,
         'https://picsum.photos/seed/mark55/300/200'),
        ('Mănuși Fitness Antiderapante XL', 320, 'Sport',
         'Mănuși cu palm-grip din silicon, ventilație pe dosul palmei și prindere velcro.', 25, 150,
         'https://picsum.photos/seed/gloves11/300/200'),
        ('Sticlă Sport Tritan BPA-Free 1L', 180, 'Sport',
         'Sticlă transparentă din plastic Tritan fără BPA, capac leak-proof, mâner integrat.', 45, 350,
         'https://picsum.photos/seed/bottle22/300/200'),
        ('Rucsac Sport Impermeabil 30L', 780, 'Sport',
         'Rucsac cu material ripstop impermeabil, compartiment laptop 15.6", buzunare laterale.', 15, 900,
         'https://picsum.photos/seed/backp33/300/200'),
        ('Sfoară pentru Sărit Ponderată — 500g', 250, 'Sport',
         'Sfoară reglabilă cu greutăți din oțel în mânere. Perfectă pentru cardio intens.', 30, 500,
         'https://picsum.photos/seed/rope44/300/200'),
        ('Interstellar — 4K Ultra HD + Blu-ray', 180, 'Filme',
         'Capodopera lui Christopher Nolan în format 4K HDR10+ cu sunet Dolby Atmos.', 20, 150,
         'https://picsum.photos/seed/movie11/300/200'),
        ('The Matrix Trilogy — 4K Remastered BoxSet', 350, 'Filme',
         'Trilogia completă Matrix remaster 4K cu bonus features extinse.', 15, 300,
         'https://picsum.photos/seed/movie22/300/200'),
        ('Card Cadou PSN PlayStation Store 50 RON', 500, 'Gaming',
         'Card digital pentru PlayStation Store. Cumpără jocuri, DLC-uri și abonamente PS Plus.', 30, 20,
         'https://picsum.photos/seed/psn33/300/200'),
        ('Card Cadou Steam 50 RON', 500, 'Gaming',
         'Card digital pentru platforma Steam. Jocuri, DLC-uri, software și iteme din Steam Market.', 30, 20,
         'https://picsum.photos/seed/steam44/300/200'),
    ]

    products = []
    for (name, price, cat, desc, stock, weight, img_url) in items:
        products.append(Product(
            name=name, price=price, category=cat,
            description=desc, stock=stock, is_active=True,
            weight_g=weight, image_url_external=img_url
        ))
    db.session.add_all(products)
    db.session.commit()


def _update_product_images():
    from .models import Product, db
    IMAGE_MAP = {
        'șampon': 'https://picsum.photos/seed/shampoo42/300/200',
        'cremă': 'https://picsum.photos/seed/cream99/300/200',
        'deodorant': 'https://picsum.photos/seed/deodor77/300/200',
        'pastă': 'https://picsum.photos/seed/tooth55/300/200',
        'gel de duș': 'https://picsum.photos/seed/shower33/300/200',
        'căști': 'https://picsum.photos/seed/headph10/300/200',
        'mouse': 'https://picsum.photos/seed/mouse21/300/200',
        'tastatură': 'https://picsum.photos/seed/keyb34/300/200',
        'hub usb': 'https://picsum.photos/seed/usbhub56/300/200',
        'cabluri': 'https://picsum.photos/seed/cable78/300/200',
        'webcam': 'https://picsum.photos/seed/webcam90/300/200',
        'tricou': 'https://picsum.photos/seed/tshirt11/300/200',
        'hanorac': 'https://picsum.photos/seed/hoodie22/300/200',
        'pantaloni': 'https://picsum.photos/seed/pants33/300/200',
        'șosete': 'https://picsum.photos/seed/socks44/300/200',
        'căciulă': 'https://picsum.photos/seed/hat55/300/200',
        'clean code': 'https://picsum.photos/seed/book101/300/200',
        'pragmatic': 'https://picsum.photos/seed/book202/300/200',
        'gândire': 'https://picsum.photos/seed/book303/300/200',
        'caiet': 'https://picsum.photos/seed/noteb44/300/200',
        'markere': 'https://picsum.photos/seed/mark55/300/200',
        'mănuși': 'https://picsum.photos/seed/gloves11/300/200',
        'sticlă': 'https://picsum.photos/seed/bottle22/300/200',
        'rucsac': 'https://picsum.photos/seed/backp33/300/200',
        'sfoară': 'https://picsum.photos/seed/rope44/300/200',
        'interstellar': 'https://picsum.photos/seed/movie11/300/200',
        'matrix': 'https://picsum.photos/seed/movie22/300/200',
        'psn': 'https://picsum.photos/seed/psn33/300/200',
        'steam': 'https://picsum.photos/seed/steam44/300/200',
    }

    changed = False
    for product in Product.query.all():
        if not product.image_filename and not product.image_url_external:
            name_lower = product.name.lower()
            for key, url in IMAGE_MAP.items():
                if key in name_lower:
                    product.image_url_external = url
                    changed = True
                    break

    if changed:
        db.session.commit()
