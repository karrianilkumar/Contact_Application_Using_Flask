"""
Bootstrap script: create admin user and assign orphaned contacts
"""
from app import app, db, User, Contact
from werkzeug.security import generate_password_hash

with app.app_context():
    print('Checking for existing admin user...')
    admin = User.query.filter_by(email='admin@example.com').first()
    
    if admin:
        print('Admin user already exists:', admin.name, admin.email)
    else:
        print('Creating admin user...')
        admin = User(
            name='Administrator',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin created: ID=%d' % admin.id)
    
    print('\nAssigning orphaned contacts to admin...')
    orphaned = Contact.query.filter(Contact.user_id == None).all()
    print('Found %d orphaned contacts' % len(orphaned))
    
    if orphaned:
        for c in orphaned:
            c.user_id = admin.id
        db.session.commit()
        print('Assigned all to admin user (ID=%d)' % admin.id)
    
    print('\nFinal counts:')
    users = db.session.query(User).count()
    contacts = db.session.query(Contact).count()
    admin_contacts = Contact.query.filter_by(user_id=admin.id).count()
    print('- Total users: %d' % users)
    print('- Total contacts: %d' % contacts)
    print('- Admin contacts: %d' % admin_contacts)
    print('\nDone. You can now login with:')
    print('  Email: admin@example.com')
    print('  Password: admin123')
