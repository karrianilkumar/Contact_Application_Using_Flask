# from app import app, db
# from sqlalchemy import text

# with app.app_context():
#     conn = db.engine.connect()
    
#     # Check and add email column
#     res = conn.execute(text("PRAGMA table_info('user')"))
#     cols = [row[1] for row in res.fetchall()]
    
#     if 'email' not in cols:
#         print('Adding email column to user table')
#         conn.execute(text('ALTER TABLE user ADD COLUMN email VARCHAR(120)'))
#         print('email column added')
#     else:
#         print('email column already exists')
    
#     if 'name' not in cols:
#         print('Adding name column to user table')
#         conn.execute(text('ALTER TABLE user ADD COLUMN name VARCHAR(100)'))
#         print('name column added')
#     else:
#         print('name column already exists')
    
#     if 'username' in cols:
#         print('username column still exists (you can manually remove it later if needed)')
    
#     conn.close()
#     print('Migration complete')
