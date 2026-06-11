# from app import app, db
# from sqlalchemy import text

# with app.app_context():
#     conn = db.engine.connect()
#     res = conn.execute(text("PRAGMA table_info('contact')"))
#     cols = [row[1] for row in res.fetchall()]
#     if 'user_id' in cols:
#         print('user_id column already exists')
#     else:
#         print('Adding user_id column to contact table')
#         conn.execute(text('ALTER TABLE contact ADD COLUMN user_id INTEGER'))
#         print('Done')
#     conn.close()
