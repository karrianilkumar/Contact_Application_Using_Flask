from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
# Werkzeug is a German word used in Python (especially with Flask).
# Pronunciation:
# English approximation: "Verk-tsoyg"
# Telugu pronunciation: "వెర్క్-త్సోయ్గ్" (or "వేర్‌క్-త్సోయ్గ్")
import datetime
import jwt
import random
import string
from sqlalchemy import or_

# Load local environment file if present
env_path = Path(__file__).resolve().parent / ".env" # to get the folder path which contains the .env file 
if env_path.exists(): # if the path is not none 
    for line in env_path.read_text().splitlines(): # convert all lines into the python list 
        if not line or line.strip().startswith("#"): # 
            continue
        key, _, value = line.partition("=") # key = db_host , _ = = , , value = "db_host_value"
        if key and value: 
            os.environ.setdefault(key.strip(), value.strip())
            # print(os.environ["DB_HOST"])
            
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# Use DATABASE_URL from environment, local .env, or fallback to SQLite for development
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///contacts.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Email configuration for OTP
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "True") == "True"
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "your-email@gmail.com")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "your-app-password")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@contactapp.com")

db = SQLAlchemy(app)
# This line attaches the database functionality to your Flask app.
# db becomes the object you use to create tables and perform database operations.
mail = Mail(app)
# This line connects email functionality to your Flask app.
# mail is the object used to send emails.

# In-memory OTP storage: {email: {"otp": "123456", "expiry": datetime, "data": {name, password_hash}}}
otp_storage = {}

# DATABASES = {
#     'default':{
#         'ENGINE':'django.db.backends.postgresql',
#         'NAME':'bus_ticket_booking_system',
#         'USER':'postgres',
#         'PASSWORD':'1234',
#         'HOST':'localhost',
#         'PORT':'5432',
#     }
# }
# Define Contact Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    username = db.Column(db.String(80), nullable=True)  # kept for backward compatibility, now optional
    role = db.Column(db.String(20), default="user")  # simple RBAC: 'user' or 'admin'
    # check_password() is a custom method used to verify whether the password entered by the user matches the hashed password stored in the database. It returns True if it matches, otherwise False.
    def check_password(self, password):
#         check_password_hash(
#     "scrypt:32768:8:1$...",
#     "admin123"
# )
        return check_password_hash(self.password_hash, password)
    


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('contacts', lazy=True))

with app.app_context():
    # Ensure database schema has new columns/tables.
    # SQLite won't modify existing tables with `create_all()`, so add missing column if needed.
    try:
        # create any missing tables first (User table might be new)
        db.create_all()
        # If using SQLite, check if `user_id` column exists on `contact` table; if not, add it.
        # PRAGMA is SQLite-specific so skip on other engines (e.g., Postgres).
        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "") or ""
        if db_uri.startswith("sqlite"):
            inspector = db.engine.execute("PRAGMA table_info('contact')")
            cols = [row[1] for row in inspector.fetchall()]
            if 'user_id' not in cols:
                # add nullable integer column for user_id
                db.engine.execute('ALTER TABLE contact ADD COLUMN user_id INTEGER')
    except Exception:
        # fallback: attempt create_all again
        db.create_all()


from functools import wraps
def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.cookies.get("jwt_token")
        
        print(f"🔍 Token in cookie: {'Yes' if token else 'No'}")
        if token:
            print(f"🔑 Token value: {token[:50]}...")
        
        if not token:
            if request.headers.get('Accept', '').startswith('text/html'):
                flash("Please login to access this page")
                return redirect(url_for('login_page'))
            return jsonify({"status": "error", "message": "Login required"}), 401
        
        try:
            payload = decode_jwt(token)
            print(f"📦 Decoded payload: {payload}")
        except Exception as e:
            print(f"❌ Decode error: {str(e)}")
            payload = None
        
        if not payload:
            if request.headers.get('Accept', '').startswith('text/html'):
                flash("Session expired. Please login again.")
                return redirect(url_for('login_page'))
            return jsonify({"status": "error", "message": "Invalid Token"}), 401
        
        user = User.query.get(payload["sub"])
        print(f"👤 User found: {user.name if user else 'None'}")
        
        if not user:
            if request.headers.get('Accept', '').startswith('text/html'):
                flash("User not found. Please login again.")
                return redirect(url_for('login_page'))
            return jsonify({"status": "error", "message": "User not found"}), 401
        
        request.user = user
        return fn(*args, **kwargs)
    
    return wrapper

# ================ OTP Helper Functions ================
def generate_otp():
    """Generate a random 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6)) # string.digits contains 0123456789 => ''.join(list)


def send_otp_email(email, otp):
    """Send OTP to user's email"""
    print(f"#### email : {email} and otp : {otp}")
    print("MAIL_SERVER     :", app.config["MAIL_SERVER"])
    print("MAIL_PORT       :", app.config["MAIL_PORT"])
    print("MAIL_USERNAME   :", app.config["MAIL_USERNAME"])
    print("MAIL_PASSWORD   :", app.config["MAIL_PASSWORD"])
    print("MAIL_SENDER     :", app.config["MAIL_DEFAULT_SENDER"])
    try:
        msg = Message(
            subject="Email Verification OTP for Contact App",
            recipients=[email],
            html=f"""
            <h2>Email Verification</h2>
            <p>Your One-Time Password (OTP) is:</p>
            <h1 style="color: #2c3e50; font-size: 32px; letter-spacing: 5px;">{otp}</h1>
            <p>This OTP is valid for <strong>10 minutes</strong>.</p>
            <p>If you did not request this verification, please ignore this email.</p>
            <hr>
            <p><em>Contact Application</em></p>
            """
        )
        mail.send(msg)
        return True
    except Exception as e:
        print("Error sending email:", str(e))
        return False


def create_otp_record(email, name, password_hash):
    """Create OTP record and send OTP to email"""
    otp = generate_otp()
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    
    otp_storage[email] = {
        "otp": otp,
        "expiry": expiry,
        "data": {
            "name": name,
            "password_hash": password_hash
        }
    }
    
    # Send OTP email
    if send_otp_email(email, otp):
        return True, "OTP sent to your email. Please verify to complete registration."
    else:
        # Remove the record if email sending failed
        if email in otp_storage:
            del otp_storage[email]
        return False, "Failed to send OTP. Please try again."


def verify_otp(email, otp):
    """Verify OTP and create user if valid"""
    if email not in otp_storage:
        return False, "No verification request found for this email."
    
    record = otp_storage[email]
    
    # Check if OTP is expired
    if datetime.datetime.utcnow() > record["expiry"]:
        del otp_storage[email]
        return False, "OTP expired. Please register again."
    
    # Check if OTP matches
    if record["otp"] != otp:
        return False, "Invalid OTP. Please try again."
    
    # OTP is valid, create user
    try:
        user_data = record["data"]
        user = User(
            name=user_data["name"],
            email=email,
            password_hash=user_data["password_hash"]
        )
        db.session.add(user)
        db.session.commit()
        
        # Remove OTP record after successful verification
        del otp_storage[email]
        
        return True, "Email verified successfully! You can now login."
    except Exception as e:
        return False, f"Error creating user: {str(e)}"

@app.route("/")
@jwt_required
def index():
    user = request.user
    if not user:
        flash("Please login to view contacts")
        return redirect(url_for('login_page'))
    
    user_id = user.id
    q = request.args.get("q")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))

    query = Contact.query.filter(Contact.user_id == user_id)
    if q:
        query = query.filter(
            or_(
                Contact.name.ilike(f"%{q}%"),
                Contact.phone_number.ilike(f"%{q}%")
            )
        )
    
    contacts = query.order_by(Contact.name).paginate(page=page, per_page=per_page, error_out=False)
    session_user = user.name if user else None
    return render_template("index.html", contacts=contacts.items, pagination=contacts, session_user=session_user)

@app.route("/update_contact/<int:id>", methods=["POST"])
@jwt_required
def update_contact(id):
    user = request.user
    user_id = user.id
    
    # Get the contact
    contact = Contact.query.get(id)
    if not contact:
        return jsonify({"status": "error", "message": "Contact not found"}), 404
    
    # Check ownership
    # is_owner = contact.user_id == user_id
    # is_admin = user and user.role == "admin"
    if contact.user_id != user_id and user.role != "admin":
        return jsonify({"status": "error", "message": "You can only edit your own contacts"}), 403
    
    # Get form data
    name = request.form.get("name", "").strip()
    phone_number = request.form.get("phone_number", "").strip()
    address = request.form.get("address", "").strip()
    
    # Track what's being updated
    updates = []
    
    # Update name if provided and different
    if name and name != contact.name:
        contact.name = name
        updates.append("name")
    
    # Update phone number if provided and different
    if phone_number and phone_number != contact.phone_number:
        # Check uniqueness (excluding this contact)
        existing = Contact.query.filter(
            Contact.phone_number == phone_number, 
            Contact.id != id,
            Contact.user_id == user_id
        ).first()
        
        if existing:
            return jsonify({
                "status": "error", 
                "message": f"Phone number '{phone_number}' already exists in your contacts!"
            }), 400
        
        contact.phone_number = phone_number
        updates.append("phone number")
    
    # Update address if provided and different
    if address and address != contact.address:
        contact.address = address
        updates.append("address")
    
    # Check if anything was actually updated
    if not updates:
        return jsonify({
            "status": "info", 
            "message": "No changes were made to the contact."
        }), 200
    
    # Save changes
    db.session.commit()
    
    return jsonify({
        "status": "success", 
        "message": f"Contact updated successfully! Updated: {', '.join(updates)}"
    }) 

@app.route("/delete_contact/<int:id>", methods=["DELETE"])
@jwt_required
def delete_contact(id):
    # user_id = session.get("user_id")
    user = request.user
    user_id = user.id
    if not user_id:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    contact = Contact.query.get(id)
    if not contact:
        return jsonify({"status": "error", "message": "Contact not found"}), 404
    
    # RBAC: only owner or admin can delete
    user = User.query.get(user_id)
    if contact.user_id != user_id and (not user or user.role != "admin"):
        return jsonify({"status": "error", "message": "You can only delete your own contacts"}), 403
    
    db.session.delete(contact)
    db.session.commit()
    return jsonify({"status": "success"})



@app.route("/add_contact", methods=["POST"])
@jwt_required
def add_contact():
    user = request.user
    user_id = user.id
    
    name = request.form.get("name")
    phone_number = request.form.get("phone_number")
    address = request.form.get("address")

    if not (name and phone_number and address):
        return jsonify({"status": "error", "message": "All fields are required!"})
    
    # Check uniqueness within user's contacts
    if Contact.query.filter_by(phone_number=phone_number, user_id=user_id).first():
        return jsonify({"status": "error", "message": "Phone number already exists in your contacts!"})
    
    new_contact = Contact(name=name, phone_number=phone_number, address=address, user_id=user_id)
    db.session.add(new_contact)
    db.session.commit()
    return jsonify({"status": "success", "contact": {"id": new_contact.id, "name": name, "phone_number": phone_number, "address": address}})

# ------------------ Authentication routes ------------------
def _jwt_secret():
    return os.environ.get("JWT_SECRET", app.secret_key)

def generate_jwt(user):
    payload = {
        "sub": str(user.id),  # ✅ Must be string
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12)
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")

def decode_jwt(token):
    try:
        print(f"🔐 Decoding token with secret: {_jwt_secret()[:10]}...")
        decoded = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
        print(f"✅ Decoded successfully: {decoded}")
        return decoded
    except jwt.ExpiredSignatureError:
        print("❌ Token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"❌ Invalid token: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return None


@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")
    
    if not name or not email or not password:
        flash("All fields are required!")
        return redirect(url_for('register_page'))
    
    # Check if user already exists
    if User.query.filter_by(email=email).first():
        flash("User with this email already exists. Please login.")
        return redirect(url_for('login_page'))
    
    # Check if OTP verification already pending for this email
    if email in otp_storage:
        flash("An OTP verification is already pending for this email. Check your inbox.")
        return redirect(url_for('verify_otp_page', email=email))
    
    # Hash password
    password_hash = generate_password_hash(password)
    
    # Create OTP record and send email
    success, message = create_otp_record(email, name, password_hash)
    
    if success:
        flash(message)
        return redirect(url_for('verify_otp_page', email=email))
    else:
        flash(message)
        return redirect(url_for('register_page'))


@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")


@app.route("/verify-otp", methods=["GET"])
def verify_otp_page():
    email = request.args.get("email", "")
    return render_template("verify_otp.html", email=email)


@app.route("/verify-otp", methods=["POST"])
def verify_otp_post():
    email = request.form.get("email")
    otp = request.form.get("otp")
    
    if not email or not otp:
        flash("Email and OTP are required!")
        return redirect(url_for('verify_otp_page', email=email))
    
    # Verify OTP and create user
    success, message = verify_otp(email, otp)
    
    if success:
        flash(message)
        return redirect(url_for('login_page'))
    else:
        flash(message)
        return redirect(url_for('verify_otp_page', email=email))

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        flash("Invalid email or password. Please try again or register.")
        return redirect(url_for('login_page'))
    
    token = generate_jwt(user)
    
    # Create response with redirect
    response = redirect(url_for('index'))
    
    # Set the cookie on the response
    response.set_cookie(
        "jwt_token",
        token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite='Lax',
        max_age=60 * 60 * 12  # 12 hours
    )
    
    # Log the cookie being set (for debugging)
    print(f"✅ Cookie set for user: {user.email}")
    print(f"🔑 Token: {token[:50]}...")
    
    return response


@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@app.route("/logout", methods=["POST", "GET"])
def logout():
    response = redirect(url_for("login_page"))
    response.delete_cookie("jwt_token")
    flash("Logged out successfully")
    return response
    # session.pop("user_id", None)
    # flash("Logged out successfully")
    # return redirect(url_for('login_page'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

# ip addr show
# if the laptop firewall is stoppoing then type this  command in the laptop :  ====> sudo ufw allow 5000
# 7032988615
    


