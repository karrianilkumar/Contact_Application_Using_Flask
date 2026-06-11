from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import jwt
import random
import string

# Load local environment file if present
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if not line or line.strip().startswith("#"):
            continue
        key, _, value = line.partition("=")
        if key and value:
            os.environ.setdefault(key.strip(), value.strip())

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
mail = Mail(app)

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

    def check_password(self, password):
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


# ================ OTP Helper Functions ================
def generate_otp():
    """Generate a random 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))


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
def index():
    # show only user's own contacts if logged in; redirect to login if not
    user_id = session.get("user_id")
    if not user_id:
        flash("Please login to view contacts")
        return redirect(url_for('login_page'))
    
    session_user = None
    q = request.args.get("q")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))

    # Show ONLY contacts belonging to the logged-in user
    query = Contact.query.filter(Contact.user_id == user_id)

    if q:
        query = query.filter(Contact.name.ilike(f"%{q}%"))

    contacts = query.order_by(Contact.name).paginate(page=page, per_page=per_page, error_out=False)
    u = User.query.get(user_id)
    session_user = u.name if u else None
    return render_template("index.html", contacts=contacts.items, pagination=contacts, session_user=session_user)

@app.route("/update_contact/<int:id>", methods=["POST"])
def update_contact(id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    contact = Contact.query.get(id)
    if not contact:
        return jsonify({"status": "error", "message": "Contact not found"}), 404
    
    # RBAC: only owner or admin can update
    user = User.query.get(user_id)
    if contact.user_id != user_id and (not user or user.role != "admin"):
        return jsonify({"status": "error", "message": "You can only edit your own contacts"}), 403
    
    name = request.form.get("name")
    phone_number = request.form.get("phone_number")
    address = request.form.get("address")

    if name:
        contact.name = name
    if phone_number:
        # Check uniqueness: another contact with same phone in user's contacts
        existing = Contact.query.filter(Contact.phone_number == phone_number, Contact.id != id, Contact.user_id == user_id).first()
        if existing:
            return jsonify({"status": "error", "message": "Phone number already exists in your contacts!"})
        contact.phone_number = phone_number
    if address:
        contact.address = address

    db.session.commit()
    return jsonify({"status": "success"})

@app.route("/delete_contact/<int:id>", methods=["DELETE"])
def delete_contact(id):
    user_id = session.get("user_id")
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
def add_contact():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
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
        "sub": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12)
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")

def decode_jwt(token):
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except Exception:
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
        # If form submission, redirect back to login with message
        if request.form:
            flash("Invalid email or password. Please try again or register.")
            return redirect(url_for('login_page'))
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401
    # create session and JWT
    session["user_id"] = user.id
    token = generate_jwt(user)
    # if form submission redirect to home
    if request.form:
        return redirect(url_for('index'))
    return jsonify({"status": "success", "token": token})


@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@app.route("/logout", methods=["POST", "GET"])
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully")
    return redirect(url_for('login_page'))


# ------------------ Simple REST API (JWT protected) ------------------
def jwt_required(fn):
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"status": "error", "message": "Missing token"}), 401
        token = auth.split(None, 1)[1]
        data = decode_jwt(token)
        if not data:
            return jsonify({"status": "error", "message": "Invalid token"}), 401
        request.user = User.query.get(data.get("sub"))
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


@app.route("/api/contacts", methods=["GET"])
@jwt_required
def api_get_contacts():
    user = request.user
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    q = request.args.get("q")
    # Show ONLY user's own contacts
    query = Contact.query.filter(Contact.user_id == user.id)
    if q:
        query = query.filter(Contact.name.ilike(f"%{q}%"))
    res = query.order_by(Contact.name).paginate(page=page, per_page=per_page, error_out=False)
    items = [{"id": c.id, "name": c.name, "phone_number": c.phone_number, "address": c.address, "user_id": c.user_id} for c in res.items]
    return jsonify({"status": "success", "contacts": items, "total": res.total, "user": user.name})


@app.route("/api/contact", methods=["POST"])
@jwt_required
def api_create_contact():
    user = request.user
    data = request.get_json() or {}
    name = data.get("name")
    phone = data.get("phone_number")
    address = data.get("address")
    if not (name and phone and address):
        return jsonify({"status": "error", "message": "name, phone_number and address required"}), 400
    if Contact.query.filter_by(phone_number=phone).first():
        return jsonify({"status": "error", "message": "Phone number exists"}), 400
    c = Contact(name=name, phone_number=phone, address=address, user_id=user.id)
    db.session.add(c)
    db.session.commit()
    return jsonify({"status": "success", "contact": {"id": c.id, "name": c.name}, "user": user.name})


@app.route("/api/contact/<int:id>", methods=["PUT", "DELETE"])
@jwt_required
def api_modify_contact(id):
    user = request.user
    contact = Contact.query.get(id)
    if not contact:
        return jsonify({"status": "error", "message": "Not found"}), 404
    if request.method == "DELETE":
        if contact.user_id != user.id and user.role != "admin":
            return jsonify({"status": "error", "message": "Forbidden"}), 403
        db.session.delete(contact)
        db.session.commit()
        return jsonify({"status": "success"})
    # PUT
    data = request.get_json() or {}
    if contact.user_id != user.id and user.role != "admin":
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    contact.name = data.get("name", contact.name)
    contact.phone_number = data.get("phone_number", contact.phone_number)
    contact.address = data.get("address", contact.address)
    db.session.commit()
    return jsonify({"status": "success", "contact": {"id": contact.id}})



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

# ip addr show
# if the laptop firewall is stoppoing then type this  command in the laptop :  ====> sudo ufw allow 5000
# 7032988615
    


