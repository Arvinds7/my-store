import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
import mysql.connector

app = Flask(__name__)
app.secret_key = "supersecretkey"   # change in production

app.config["UPLOAD_FOLDER"] = "static/uploads"

bcrypt = Bcrypt(app)

# ---------------- DATABASE CONNECTION ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="#",          # put your MySQL password
    database="login_system"
)

cursor = db.cursor(dictionary=True)


# ---------------- HOME (LOGIN PAGE) ----------------
@app.route("/")
def login():
    return render_template("login.html")


# ---------------- REGISTER PAGE ----------------
@app.route("/register")
def register():
    return render_template("register.html")


# ---------------- REGISTER USER ----------------
@app.route("/register_user", methods=["POST"])
def register_user():
    email = request.form["email"].strip()
    password = request.form["password"].strip()

    if not email or not password:
        flash("All fields are required!", "danger")
        return redirect(url_for("register"))

    # Check if email already exists
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()

    if user:
        flash("Email already exists!", "danger")
        return redirect(url_for("register"))

    # Hash password
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    cursor.execute(
        "INSERT INTO users (email, password) VALUES (%s, %s)",
        (email, hashed_password)
    )
    db.commit()

    flash("Registration successful! Please login.", "success")
    return redirect(url_for("login"))


# ---------------- LOGIN USER ----------------
@app.route("/login_user", methods=["POST"])
def login_user():
    email = request.form["email"].strip()
    password = request.form["password"].strip()
    remember = request.form.get("remember")

    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()

    if user and bcrypt.check_password_hash(user["password"], password):

        session["user"] = user["email"]

        if remember:
            session.permanent = True

        return redirect(url_for("dashboard"))

    else:
        flash("Invalid email or password", "danger")
        return redirect(url_for("login"))


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" in session:

        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()

        return render_template(
            "dashboard.html",
            user=session["user"],
            products=products
        )
    else:
        flash("Please login first!", "danger")
        return redirect(url_for("login"))


# 🔥 ADD TO CART ROUTE (Outside dashboard)
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):

    if "cart" not in session:
        session["cart"] = {}

    cart = session["cart"]

    if str(product_id) in cart:
        cart[str(product_id)] += 1
    else:
        cart[str(product_id)] = 1

    session["cart"] = cart
    flash("Product added to cart!", "success")

    return redirect(url_for("dashboard"))

# ---------------- CART PAGE ----------------
@app.route("/cart")
def cart():

    if "cart" not in session or not session["cart"]:
        return render_template("cart.html", products=[])

    cart = session["cart"]
    product_ids = tuple(cart.keys())

    format_strings = ','.join(['%s'] * len(product_ids))

    cursor.execute(f"SELECT * FROM products WHERE id IN ({format_strings})", product_ids)
    products = cursor.fetchall()

    return render_template("cart.html", products=products, cart=cart)    
    

# ---------------- CHECKOUT PAGE ----------------        
@app.route("/checkout")
def checkout():

    if "cart" not in session:
        return redirect(url_for("dashboard"))

    cart = session["cart"]
    product_ids = tuple(cart.keys())

    format_strings = ','.join(['%s'] * len(product_ids))

    cursor.execute(f"SELECT * FROM products WHERE id IN ({format_strings})", product_ids)
    products = cursor.fetchall()

    total = 0
    for product in products:
        total += float(product["price"]) * cart[str(product["id"])]

    cursor.execute(
        "INSERT INTO orders (user_email, total) VALUES (%s, %s)",
        (session["user"], total)
    )
    db.commit()

    session.pop("cart", None)

    flash("Order placed successfully!", "success")
    return redirect(url_for("dashboard"))


# ---------------- ADMIN PAGE ----------------
@app.route("/admin")
def admin():
    if "user" not in session:
     return redirect(url_for("login"))
     
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    return render_template("admin.html", products=products)


# ---------------- ADD PRODUCT ----------------
@app.route("/add_product", methods=["POST"])
def add_product():

    if "user" not in session:
        return redirect(url_for("login"))

    name = request.form["name"]
    price = request.form["price"]

    file = request.files["image"]

    if file.filename == "":
        flash("No file selected!", "danger")
        return redirect(url_for("admin"))

    filename = file.filename
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)

    cursor.execute(
        "INSERT INTO products (name, price, image) VALUES (%s, %s, %s)",
        (name, price, filename)
    )
    db.commit()

    flash("Product added successfully!", "success")
    return redirect(url_for("admin"))


# ---------------- SALES DASBOARD ----------------
@app.route("/sales")
def sales():

    cursor.execute("""
        SELECT DATE(order_date) as day, SUM(total) as total_sales
        FROM orders
        GROUP BY DATE(order_date)
    """)
    data = cursor.fetchall()

    return render_template("sales.html", data=data)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("login"))


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)
