from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///contacts.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Database Model
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False, unique=True)
    address = db.Column(db.String(200), nullable=False)

# Function to insert dummy data
def insert_dummy_data():
    if Contact.query.count() == 0:  # Avoid duplicate inserts
        contacts = [
            Contact(name="Alice", phone_number="9876543210", address="New York"),
            Contact(name="Bob", phone_number="8765432109", address="California"),
            Contact(name="Charlie", phone_number="7654321098", address="Texas"),
        ]
        db.session.add_all(contacts)
        db.session.commit()

# Run database creation and data insertion inside app context
with app.app_context():
    db.create_all()
    insert_dummy_data()

@app.route("/")
def index():
    contacts = Contact.query.all()
    return render_template("index.html", contacts=contacts)

if __name__ == "__main__":
    app.run(debug=True)

