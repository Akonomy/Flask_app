from flask import Blueprint, render_template, request, abort, jsonify
from flask_login import current_user
from ..models import Product, WishlistItem, db

products_bp = Blueprint('products', __name__)


@products_bp.route('/')
def list_products():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()
    per_page = 12

    query = Product.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    query = query.order_by(Product.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    categories = db.session.query(Product.category).filter(
        Product.is_active == True,
        Product.category.isnot(None),
        Product.category != ''
    ).distinct().all()
    categories = sorted([c[0] for c in categories])

    wishlist_ids = set()
    if current_user.is_authenticated:
        rows = WishlistItem.query.filter_by(user_id=current_user.id).all()
        wishlist_ids = {r.product_id for r in rows}

    return render_template('products/list.html',
                           products=pagination,
                           categories=categories,
                           current_category=category,
                           search=search,
                           wishlist_ids=wishlist_ids)


@products_bp.route('/categories')
def categories_json():
    cats = db.session.query(Product.category).filter(
        Product.is_active == True,
        Product.category.isnot(None),
        Product.category != ''
    ).distinct().all()
    return jsonify([c[0] for c in sorted(cats)])


@products_bp.route('/<int:product_id>')
def detail(product_id):
    product = Product.query.get_or_404(product_id)
    if not product.is_active:
        if not current_user.is_authenticated or current_user.role_level < 2:
            abort(404)

    wishlisted = False
    if current_user.is_authenticated:
        wishlisted = WishlistItem.query.filter_by(
            user_id=current_user.id, product_id=product_id).first() is not None

    return render_template('products/detail.html', product=product, wishlisted=wishlisted)
