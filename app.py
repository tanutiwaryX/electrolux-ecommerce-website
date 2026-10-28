"""ElectroLux: beginner-friendly Flask e-commerce demonstration."""
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import or_, func
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, instance_relative_config=True)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or "dev-only-change-this-key-before-deployment"
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'instance' / 'electrolux.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["WTF_CSRF_TIME_LIMIT"] = 3600
os.makedirs(app.instance_path, exist_ok=True)
db = SQLAlchemy(app)
csrf = CSRFProtect(app)

ORDER_STATUSES = ["Placed", "Confirmed", "Packed", "Shipped", "Delivered", "Cancelled"]
CATEGORIES = ["Smartphones", "Laptops", "Headphones", "Smartwatches", "Cameras", "Accessories"]

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    orders = db.relationship("Order", back_populates="user", cascade="all, delete-orphan")
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(60), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    specifications = db.Column(db.Text, nullable=False, default="")
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(600), nullable=False, default="")
    featured = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    order_items = db.relationship("OrderItem", back_populates="product")
    __table_args__ = (db.CheckConstraint("price >= 0", name="check_product_price_nonnegative"),
                      db.CheckConstraint("stock >= 0", name="check_product_stock_nonnegative"))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="Placed")
    total = db.Column(db.Numeric(10, 2), nullable=False)
    shipping_name = db.Column(db.String(120), nullable=False)
    shipping_email = db.Column(db.String(180), nullable=False)
    shipping_phone = db.Column(db.String(40), nullable=False)
    shipping_address = db.Column(db.String(250), nullable=False)
    shipping_city = db.Column(db.String(100), nullable=False)
    shipping_postal_code = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    product_name = db.Column(db.String(160), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")
    __table_args__ = (db.CheckConstraint("quantity > 0", name="check_order_item_quantity_positive"),)

def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None

@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "categories": CATEGORIES, "order_statuses": ORDER_STATUSES}

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Please sign in with the administrator account.", "info")
            return redirect(url_for("login", next=request.path))
        if not user.is_admin:
            abort(403)
        return fn(*args, **kwargs)
    return wrapped

def cart_items():
    cart = session.get("cart", {})
    result, total = [], Decimal("0.00")
    for key, qty in cart.items():
        product = db.session.get(Product, int(key))
        if not product or product.stock < 1:
            continue
        qty = max(1, min(int(qty), product.stock))
        line = product.price * qty
        result.append({"product": product, "quantity": qty, "line_total": line})
        total += line
    return result, total

@app.template_filter("money")
def money(value):
    return f"₹{Decimal(value):,.2f}"

@app.route("/")
def index():
    featured = Product.query.filter_by(featured=True).order_by(Product.id).limit(8).all()
    if not featured:
        featured = Product.query.order_by(Product.id.desc()).limit(8).all()
    bestsellers = Product.query.filter(Product.stock > 0).order_by(Product.id.desc()).limit(4).all()
    return render_template("index.html", featured=featured, bestsellers=bestsellers)

@app.route("/products")
def products():
    query = Product.query
    keyword = request.args.get("q", "").strip()[:100]
    category = request.args.get("category", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()
    sort = request.args.get("sort", "featured")
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(Product.name.ilike(like), Product.description.ilike(like), Product.category.ilike(like)))
    if category in CATEGORIES:
        query = query.filter_by(category=category)
    try:
        if min_price: query = query.filter(Product.price >= max(0, Decimal(min_price)))
        if max_price: query = query.filter(Product.price <= max(0, Decimal(max_price)))
    except InvalidOperation:
        flash("Please enter valid price filters.", "warning")
    if sort == "price_asc": query = query.order_by(Product.price.asc())
    elif sort == "price_desc": query = query.order_by(Product.price.desc())
    elif sort == "newest": query = query.order_by(Product.created_at.desc())
    else: query = query.order_by(Product.featured.desc(), Product.id.asc())
    page = request.args.get("page", 1, type=int)
    pagination = query.paginate(page=max(page, 1), per_page=9, error_out=False)
    return render_template("products.html", pagination=pagination, keyword=keyword,
                           selected_category=category, min_price=min_price, max_price=max_price, sort=sort)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = db.get_or_404(Product, product_id)
    related = Product.query.filter(Product.category == product.category, Product.id != product.id).limit(4).all()
    return render_template("product_detail.html", product=product, related=related)

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user(): return redirect(url_for("index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(name) < 2 or len(name) > 100 or "@" not in email or len(email) > 180 or len(password) < 8:
            flash("Enter a valid name and email. Passwords must be at least 8 characters.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "warning")
        else:
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user); db.session.commit()
            session.clear(); session["user_id"] = user.id
            flash("Welcome to ElectroLux. Your account is ready.", "success")
            return redirect(url_for("index"))
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user(): return redirect(url_for("admin_dashboard") if current_user().is_admin else url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session.clear(); session["user_id"] = user.id
            flash("You're signed in.", "success")
            target = request.args.get("next", "")
            if target.startswith("/") and not target.startswith("//"): return redirect(target)
            return redirect(url_for("admin_dashboard") if user.is_admin else url_for("index"))
        flash("Email or password is incorrect.", "danger")
    return render_template("auth.html", mode="login")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))

@app.route("/cart")
def cart():
    items, total = cart_items()
    return render_template("cart.html", items=items, total=total)

@app.route("/cart/add/<int:product_id>", methods=["POST"])
def cart_add(product_id):
    product = db.get_or_404(Product, product_id)
    if product.stock < 1:
        flash("This product is currently out of stock.", "warning")
    else:
        cart = session.get("cart", {})
        try: qty = int(request.form.get("quantity", 1))
        except ValueError: qty = 1
        qty = max(1, min(qty, product.stock))
        cart[str(product.id)] = min(int(cart.get(str(product.id), 0)) + qty, product.stock)
        session["cart"] = cart
        flash(f"{product.name} added to your cart.", "success")
    return redirect(request.referrer if request.referrer and request.referrer.startswith("/") else url_for("cart"))

@app.route("/cart/update", methods=["POST"])
def cart_update():
    cart = session.get("cart", {})
    for key in list(cart):
        raw = request.form.get(f"quantity_{key}")
        if raw is None: continue
        try: qty = int(raw)
        except ValueError: qty = 1
        product = db.session.get(Product, int(key))
        if not product or qty <= 0: cart.pop(key, None)
        else: cart[key] = min(qty, product.stock)
    session["cart"] = cart
    flash("Cart updated.", "success")
    return redirect(url_for("cart"))

@app.route("/cart/remove/<int:product_id>", methods=["POST"])
def cart_remove(product_id):
    cart = session.get("cart", {}); cart.pop(str(product_id), None); session["cart"] = cart
    flash("Item removed from your cart.", "info")
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items, total = cart_items()
    if not items:
        flash("Your cart is empty. Add something you love first.", "info")
        return redirect(url_for("products"))
    user = current_user()
    if request.method == "POST":
        fields = {key: request.form.get(key, "").strip() for key in
                  ["shipping_name", "shipping_email", "shipping_phone", "shipping_address", "shipping_city", "shipping_postal_code"]}
        if any(not value for value in fields.values()) or "@" not in fields["shipping_email"] or any(len(v) > limit for v, limit in zip(fields.values(), [120,180,40,250,100,20])):
            flash("Please complete all shipping fields with valid values.", "danger")
            return render_template("checkout.html", items=items, total=total, user=user)
        try:
            for item in items:
                product = db.session.get(Product, item["product"].id)
                if not product or product.stock < item["quantity"]:
                    raise ValueError("Stock changed while you were checking out. Please review your cart.")
            order = Order(user_id=user.id, total=total, status="Placed", **fields)
            db.session.add(order); db.session.flush()
            for item in items:
                product = db.session.get(Product, item["product"].id)
                product.stock -= item["quantity"]
                db.session.add(OrderItem(order_id=order.id, product_id=product.id, product_name=product.name,
                                         unit_price=product.price, quantity=item["quantity"]))
            db.session.commit()
            session["cart"] = {}
            flash("Demo order placed successfully. No payment was collected.", "success")
            return redirect(url_for("order_detail", order_id=order.id))
        except ValueError as exc:
            db.session.rollback(); flash(str(exc), "warning")
            return redirect(url_for("cart"))
    return render_template("checkout.html", items=items, total=total, user=user)

@app.route("/orders")
@login_required
def orders():
    page = request.args.get("page", 1, type=int)
    pagination = Order.query.filter_by(user_id=current_user().id).order_by(Order.created_at.desc()).paginate(page=max(1,page), per_page=10, error_out=False)
    return render_template("orders.html", pagination=pagination)

@app.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = db.get_or_404(Order, order_id)
    if order.user_id != current_user().id and not current_user().is_admin: abort(403)
    return render_template("order_detail.html", order=order)

@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    user = current_user()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if len(name) < 2 or len(name) > 100:
            flash("Name must be between 2 and 100 characters.", "danger")
        else:
            user.name = name; db.session.commit(); flash("Profile updated.", "success")
            return redirect(url_for("account"))
    return render_template("account.html", user=user)

@app.errorhandler(403)
def forbidden(error): return render_template("error.html", code=403, message="You don't have permission to view this page."), 403
@app.errorhandler(404)
def not_found(error): return render_template("error.html", code=404, message="We couldn't find that page or product."), 404
@app.errorhandler(500)
def server_error(error):
    db.session.rollback()
    return render_template("error.html", code=500, message="Something went wrong. Please try again."), 500

@app.route("/admin")
@admin_required
def admin_dashboard():
    product_count = Product.query.count()
    order_count = Order.query.count()
    customer_count = User.query.filter_by(is_admin=False).count()
    revenue = db.session.query(func.coalesce(func.sum(Order.total), 0)).filter(Order.status != "Cancelled").scalar()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(6).all()
    return render_template("admin/dashboard.html", product_count=product_count, order_count=order_count,
                           customer_count=customer_count, revenue=revenue, recent_orders=recent_orders)

@app.route("/admin/products")
@admin_required
def admin_products():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("admin/products.html", products=products)

@app.route("/admin/products/new", methods=["GET", "POST"])
@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_product_form(product_id=None):
    product = db.session.get(Product, product_id) if product_id else None
    if product_id and not product: abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        specifications = request.form.get("specifications", "").strip()
        image_url = request.form.get("image_url", "").strip()
        try:
            price = Decimal(request.form.get("price", ""))
            stock = int(request.form.get("stock", ""))
            if not price.is_finite() or price < 0 or price > Decimal("99999999.99") or stock < 0 or stock > 1000000: raise ValueError
        except (ValueError, InvalidOperation):
            flash("Enter a valid non-negative price and whole-number stock.", "danger")
            return render_template("admin/product_form.html", product=product)
        if not name or len(name) > 160 or category not in CATEGORIES or not description or len(description) > 5000 or len(specifications) > 5000 or len(image_url) > 600 or (image_url and not image_url.startswith(("https://", "http://", "/static/"))):
            flash("Please check all fields. Category and image URL must be valid.", "danger")
            return render_template("admin/product_form.html", product=product)
        if not product: product = Product()
        product.name=name; product.category=category; product.description=description
        product.specifications=specifications; product.price=price; product.stock=stock
        product.image_url=image_url; product.featured=bool(request.form.get("featured"))
        db.session.add(product); db.session.commit()
        flash("Product saved.", "success"); return redirect(url_for("admin_products"))
    return render_template("admin/product_form.html", product=product)

@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def admin_product_delete(product_id):
    product = db.get_or_404(Product, product_id)
    if product.order_items:
        flash("This product is in order history and cannot be deleted. Set stock to zero instead.", "warning")
    else:
        db.session.delete(product); db.session.commit(); flash("Product deleted.", "success")
    return redirect(url_for("admin_products"))

@app.route("/admin/orders")
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=orders)

@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def admin_order_status(order_id):
    order = db.get_or_404(Order, order_id)
    status = request.form.get("status", "")
    if status not in ORDER_STATUSES:
        flash("Invalid order status.", "danger")
    elif order.status == "Cancelled" and status != "Cancelled":
        flash("Cancelled orders cannot be reopened in this demo.", "warning")
    elif status == "Cancelled" and order.status != "Cancelled":
        for item in order.items:
            product = db.session.get(Product, item.product_id)
            if product: product.stock += item.quantity
        order.status = status; db.session.commit(); flash("Order cancelled and stock restored.", "success")
    else:
        order.status = status; db.session.commit(); flash("Order status updated.", "success")
    return redirect(url_for("admin_orders"))

@app.route("/admin/customers")
@admin_required
def admin_customers():
    customers = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).all()
    return render_template("admin/customers.html", customers=customers)

SEED_PRODUCTS = [
("Nova X Pro 256GB","Smartphones","Flagship performance, vivid AMOLED display and a versatile triple-camera system.","6.7-inch AMOLED; 256GB; 5G; 50MP camera",79999,12,"photo-1592899677977-9c10ca588bbd",True),
("Pixel One 128GB","Smartphones","A clean, intelligent smartphone experience with exceptional computational photography.","6.3-inch OLED; 128GB; 5G; all-day battery",59999,18,"photo-1511707171634-5f897ff02aa9",True),
("iPhone 15 128GB","Smartphones","Elegant design, smooth performance and reliable everyday photography.","6.1-inch OLED; 128GB; Face ID; USB-C",69999,9,"photo-1592750475338-74b7b21085ab",False),
("Galaxy A55 5G","Smartphones","A balanced everyday phone with a bright display and long-lasting battery.","6.6-inch Super AMOLED; 128GB; 5G",32999,20,"photo-1512499617640-c74ae3a79d37",False),
("AeroBook Pro 14","Laptops","A lightweight productivity laptop designed for focused work and creative projects.","14-inch display; 16GB RAM; 512GB SSD; Wi-Fi 6",114999,7,"photo-1496181133206-80ce9b88a853",True),
("ZenBook Air 13","Laptops","Portable power in a premium aluminium chassis, ready for work on the move.","13.3-inch display; 16GB RAM; 1TB SSD",94999,6,"photo-1517336714731-489689fd1ca8",True),
("ThinkPad E14","Laptops","A dependable business laptop with a comfortable keyboard and robust build.","14-inch FHD; 16GB RAM; 512GB SSD",68999,10,"photo-1496181133206-80ce9b88a853",False),
("Creator Studio 16","Laptops","A colour-rich screen and powerful components for design and media workflows.","16-inch display; 32GB RAM; 1TB SSD",149999,4,"photo-1516387938699-a93567ec168e",False),
("Sonic ANC Headphones","Headphones","Immersive sound and adaptive noise cancellation for travel and deep focus.","Bluetooth 5.3; ANC; 35-hour battery; USB-C",12999,25,"photo-1505740420928-5e560c06d30e",True),
("Studio Buds Pro","Headphones","Compact wireless earbuds with crisp calls and a pocket-sized charging case.","Wireless; ANC; IPX4; 24-hour case battery",8999,30,"photo-1606220945770-b5b6c2c55bf1",False),
("Pulse Wireless Headset","Headphones","Comfort-first wireless audio with punchy bass and a foldable design.","Bluetooth 5.2; 30-hour battery; built-in mic",4999,22,"photo-1546435770-a3e426bf472b",False),
("QuietComfort Lite","Headphones","Soft over-ear cushions and balanced sound for everyday listening.","Over-ear; Bluetooth; 28-hour battery",7499,15,"photo-1505740420928-5e560c06d30e",False),
("FitWatch Series 4","Smartwatches","Track workouts, sleep and notifications from a crisp always-ready display.","AMOLED; GPS; heart-rate tracking; 7-day battery",15999,14,"photo-1523275335684-37898b6baf30",True),
("Active Smartwatch S","Smartwatches","A sleek daily companion with activity tracking and water resistance.","1.8-inch display; GPS; 5 ATM; Bluetooth calling",8999,19,"photo-1524805444758-089113d48a6d",False),
("Lumina Mirrorless M50","Cameras","A compact mirrorless camera made for travel, portraits and content creation.","24MP APS-C; 4K video; interchangeable lens mount",64999,5,"photo-1516035069371-29a1b244cc32",True),
("ActionCam 4K","Cameras","Capture adventures in sharp 4K with a rugged, travel-ready body.","4K video; waterproof housing; image stabilisation",18999,8,"photo-1502920917128-1aa500764cbd",False),
("65W GaN Fast Charger","Accessories","A compact multi-device charger with intelligent power delivery.","65W USB-C PD; dual port; over-current protection",2499,50,"photo-1583394838336-acd977736f90",False),
("Everyday USB-C Hub","Accessories","Expand a laptop's connectivity with one tidy, travel-friendly hub.","USB-C; HDMI; USB-A; SD reader",3299,35,"photo-1625842268584-8f3296236761",False),
("Magnetic Wireless Stand","Accessories","A minimalist charging stand for a tidy desk and convenient viewing.","Wireless charging; adjustable angle; USB-C input",2799,28,"photo-1609592806596-b43bada5a4d0",False),
("Precision Bluetooth Mouse","Accessories","A quiet, ergonomic mouse designed for productive days and precise control.","Bluetooth; adjustable DPI; rechargeable",1999,40,"photo-1583394838336-acd977736f90",False),
]

def seed_database():
    """Create tables and seed records only when they are missing."""
    db.create_all()
    admin = User.query.filter_by(email="admin@electrolux.demo").first()
    if not admin:
        admin = User(name="ElectroLux Admin", email="admin@electrolux.demo", is_admin=True)
        admin.set_password(os.getenv("DEMO_ADMIN_PASSWORD", "ElectroLuxDemo!2026"))
        db.session.add(admin)
    for row in SEED_PRODUCTS:
        name, category, description, specs, price, stock, photo, featured = row
        if Product.query.filter_by(name=name).first(): continue
        image_url = f"https://images.unsplash.com/{photo}?auto=format&fit=crop&w=1000&q=85" if not photo.startswith("photo- ") else "/static/img/product-placeholder.svg"
        db.session.add(Product(name=name, category=category, description=description, specifications=specs,
                               price=price, stock=stock, image_url=image_url, featured=featured))
    db.session.commit()

with app.app_context():
    seed_database()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
