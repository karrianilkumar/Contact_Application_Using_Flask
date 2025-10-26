from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "supersecretkey"

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:Anil12345@localhost/contact_db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

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
        field = request.form.get("field")
        value = request.form.get("value")

        if field == "name":
            contact.name = value
        elif field == "phone_number":
            contact.phone_number = value
        elif field == "address":
            contact.address = value

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
    


