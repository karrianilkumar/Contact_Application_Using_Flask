import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

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

db = SQLAlchemy(app)

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
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), unique=True, nullable=False)
    address = db.Column(db.String(200), nullable=False)

with app.app_context():
    db.create_all()

@app.route("/")
def index():
    contacts = Contact.query.order_by(Contact.name).all()  # Sorting by name
    return render_template("index.html", contacts=contacts)

@app.route("/update_contact/<int:id>", methods=["POST"])
def update_contact(id):
    contact = Contact.query.get(id)
    if contact:
        name = request.form.get("name")
        phone_number = request.form.get("phone_number")
        address = request.form.get("address")

        if name:
            contact.name = name
        if phone_number:
            if Contact.query.filter(Contact.phone_number == phone_number, Contact.id != id).first():
                return jsonify({"status": "error", "message": "Phone number already exists!"})
            contact.phone_number = phone_number
        if address:
            contact.address = address

        db.session.commit()
        return jsonify({"status": "success"})

    return jsonify({"status": "error", "message": "Contact not found"}), 404

@app.route("/delete_contact/<int:id>", methods=["DELETE"])
def delete_contact(id):
    contact = Contact.query.get(id)
    if contact:
        db.session.delete(contact)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Contact not found"}), 404

@app.route("/add_contact", methods=["POST"])
def add_contact():
    name = request.form.get("name")
    phone_number = request.form.get("phone_number")
    address = request.form.get("address")

    if name and phone_number and address:
        if Contact.query.filter_by(phone_number=phone_number).first():
            return jsonify({"status": "error", "message": "Phone number already exists!"})
        else:
            new_contact = Contact(name=name, phone_number=phone_number, address=address)
            db.session.add(new_contact)
            db.session.commit()
            return jsonify({"status": "success", "contact": {"id": new_contact.id, "name": name, "phone_number": phone_number, "address": address}})
    
    return jsonify({"status": "error", "message": "All fields are required!"})



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


    
# ip addr show
# if the laptop firewall is stoppoing then type this  command in the laptop :  ====> sudo ufw allow 5000
# 7032988615
    


