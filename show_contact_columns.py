from app import app, db
from sqlalchemy import text

with app.app_context():
    print('Using DB URI:', app.config.get('SQLALCHEMY_DATABASE_URI'))
    conn = db.engine.connect()
    res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='contact' ORDER BY ordinal_position"))
    rows = res.fetchall()
    print('contact columns:')
    for r in rows:
        print(' -', r[0], r[1])
    conn.close()
